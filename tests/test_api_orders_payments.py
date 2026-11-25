"""API tests for checkout, order persistence, payment config, validation, and idempotency."""

import uuid
import pytest
import requests

pytestmark = pytest.mark.api


def _create_sample_order(api_base_url, headers):
    requests.delete(f"{api_base_url}/api/cart", headers=headers, timeout=5)
    products = requests.get(f"{api_base_url}/api/products", timeout=5).json()
    requests.post(
        f"{api_base_url}/api/cart/items",
        json={"product_id": products[0]["id"], "quantity": 1},
        headers=headers,
        timeout=5,
    )
    resp = requests.post(
        f"{api_base_url}/api/orders/checkout",
        json={
            "customer_name": "Alex Mercer",
            "customer_email": "customer@payflow.dev",
            "customer_phone": "+14155550101",
            "shipping_address": "100 Main Street",
            "shipping_city": "San Francisco",
            "shipping_postal_code": "94105",
            "shipping_country": "United States",
        },
        headers=headers,
        timeout=5,
    )
    assert resp.status_code == 201
    return resp.json()


def test_payment_config_never_exposes_secrets(api_base_url):
    resp = requests.get(f"{api_base_url}/api/payments/config", timeout=5)
    assert resp.status_code == 200
    body_text = resp.text
    assert "sk_test_" not in body_text
    assert "sk_live_" not in body_text
    assert "whsec_" not in body_text
    assert "RAZORPAY_KEY_SECRET" not in body_text


def test_checkout_validation_and_empty_cart(api_base_url, customer_headers):
    requests.delete(f"{api_base_url}/api/cart", headers=customer_headers, timeout=5)
    empty_resp = requests.post(
        f"{api_base_url}/api/orders/checkout",
        json={
            "customer_name": "Alex Mercer",
            "customer_email": "customer@payflow.dev",
            "customer_phone": "+14155550101",
            "shipping_address": "100 Main Street",
            "shipping_city": "San Francisco",
            "shipping_postal_code": "94105",
            "shipping_country": "United States",
        },
        headers=customer_headers,
        timeout=5,
    )
    assert empty_resp.status_code == 400

    # Invalid phone rejected by Pydantic validator
    invalid_phone = requests.post(
        f"{api_base_url}/api/orders/checkout",
        json={
            "customer_name": "Alex Mercer",
            "customer_email": "customer@payflow.dev",
            "customer_phone": "123",
            "shipping_address": "100 Main Street",
            "shipping_city": "San Francisco",
            "shipping_postal_code": "94105",
            "shipping_country": "United States",
        },
        headers=customer_headers,
        timeout=5,
    )
    assert invalid_phone.status_code == 422


def test_order_authorization_and_live_or_unconfigured_gateway(api_base_url, customer_headers, admin_headers):
    order = _create_sample_order(api_base_url, customer_headers)
    assert order["status"] == "pending"

    # Register another user and verify they cannot view or pay for customer's order
    other_email = f"other_{uuid.uuid4().hex[:6]}@payflow.dev"
    other_tok = requests.post(
        f"{api_base_url}/api/auth/register",
        json={"email": other_email, "full_name": "Other User", "password": "Password@123"},
        timeout=5,
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_tok}"}

    forbidden_order = requests.get(f"{api_base_url}/api/orders/{order['id']}", headers=other_headers, timeout=5)
    assert forbidden_order.status_code == 403

    forbidden_pay = requests.post(
        f"{api_base_url}/api/payments/initiate",
        json={"order_id": order["id"], "provider": "stripe", "payment_method": "card"},
        headers=other_headers,
        timeout=5,
    )
    assert forbidden_pay.status_code == 403

    cfg = requests.get(f"{api_base_url}/api/payments/config", timeout=5).json()
    idem_key = f"idem-{order['id']}-{uuid.uuid4().hex[:8]}"
    if cfg["stripe_configured"]:
        r1 = requests.post(
            f"{api_base_url}/api/payments/initiate",
            json={"order_id": order["id"], "provider": "stripe", "payment_method": "card", "idempotency_key": idem_key},
            headers=customer_headers,
            timeout=15,
        )
        assert r1.status_code == 201
        r2 = requests.post(
            f"{api_base_url}/api/payments/initiate",
            json={"order_id": order["id"], "provider": "stripe", "payment_method": "card", "idempotency_key": idem_key},
            headers=customer_headers,
            timeout=15,
        )
        assert r2.status_code == 201
        assert r1.json()["payment"]["id"] == r2.json()["payment"]["id"]
    else:
        r1 = requests.post(
            f"{api_base_url}/api/payments/initiate",
            json={"order_id": order["id"], "provider": "stripe", "payment_method": "card", "idempotency_key": idem_key},
            headers=customer_headers,
            timeout=5,
        )
        assert r1.status_code == 503

    # Cancel order succeeds before payment capture
    cancel_resp = requests.post(f"{api_base_url}/api/orders/{order['id']}/cancel", headers=customer_headers, timeout=5)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


def test_verify_rejects_mismatched_gateway_order_id_and_cancel_syncs_payment(api_base_url, customer_headers):
    from app.database import SessionLocal
    from app.models import Order, Payment, Product, User

    order = _create_sample_order(api_base_url, customer_headers)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "customer@payflow.dev").first()
        payment = Payment(
            order_id=order["id"],
            user_id=user.id,
            provider="stripe",
            payment_method="card",
            gateway_order_id=f"pi_expected_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"mismatch-{uuid.uuid4().hex[:8]}",
            amount_cents=order["total_cents"],
            currency="USD",
            status="created",
        )
        db.add(payment)
        db.commit()
        payment_id = payment.id
    finally:
        db.close()

    # Spoofed gateway_order_id belonging to another PaymentIntent must be rejected with 400
    spoof_resp = requests.post(
        f"{api_base_url}/api/payments/verify",
        json={"payment_id": payment_id, "gateway_order_id": "pi_another_users_cheaper_order"},
        headers=customer_headers,
        timeout=5,
    )
    assert spoof_resp.status_code == 400
    assert "mismatch" in spoof_resp.json()["detail"].lower()

    # Cancelling the order must also synchronize the open Payment row to cancelled
    cancel_order_resp = requests.post(
        f"{api_base_url}/api/orders/{order['id']}/cancel",
        headers=customer_headers,
        timeout=5,
    )
    assert cancel_order_resp.status_code == 200
    data = cancel_order_resp.json()
    assert data["status"] == "cancelled"
    assert data["payments"][0]["status"] == "cancelled"
