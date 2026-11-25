"""API tests for webhook cryptographic signature verification, deduplication, and order sync."""

import hashlib
import hmac
import json
import os
import time
import uuid

import pytest
import requests

pytestmark = pytest.mark.api


def _sign_stripe_payload(payload_bytes: bytes, secret: str) -> str:
    ts = str(int(time.time()))
    signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _sign_razorpay_payload(payload_str: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()


def _insert_order_and_payment(provider: str, gateway_order_id: str):
    """Insert an Order + Payment row directly via backend models to test webhook sync deterministically."""
    from app.database import SessionLocal
    from app.models import Order, OrderItem, Payment, Product, User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "customer@payflow.dev").first()
        product = db.query(Product).first()
        order = Order(
            order_number=f"PF-WH-{uuid.uuid4().hex[:6].upper()}",
            user_id=user.id,
            status="payment_initiated",
            subtotal_cents=product.price_cents,
            tax_cents=0,
            total_cents=product.price_cents,
            currency="USD",
            customer_name=user.full_name,
            customer_email=user.email,
            customer_phone="+14155550101",
            shipping_address="1 Webhook Way",
            shipping_city="Austin",
            shipping_postal_code="78701",
            shipping_country="USA",
        )
        db.add(order)
        db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                unit_price_cents=product.price_cents,
                quantity=1,
                line_total_cents=product.price_cents,
            )
        )
        payment = Payment(
            order_id=order.id,
            user_id=user.id,
            provider=provider,
            payment_method="card",
            gateway_order_id=gateway_order_id,
            idempotency_key=f"wh-idem-{uuid.uuid4().hex[:10]}",
            amount_cents=product.price_cents,
            currency="USD" if provider == "stripe" else "INR",
            status="pending",
        )
        db.add(payment)
        db.commit()
        return order.id, payment.id
    finally:
        db.close()


def test_stripe_webhook_signature_and_idempotency(api_base_url, customer_headers):
    pi_id = f"pi_test_{uuid.uuid4().hex[:10]}"
    order_id, _ = _insert_order_and_payment("stripe", pi_id)

    event_payload = {
        "id": f"evt_test_{uuid.uuid4().hex[:12]}",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": pi_id,
                "object": "payment_intent",
                "status": "succeeded",
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    # 1. Invalid signature must be rejected with 400
    bad_resp = requests.post(
        f"{api_base_url}/api/webhooks/stripe",
        data=raw_bytes,
        headers={"Stripe-Signature": "t=123,v1=deadbeef", "Content-Type": "application/json"},
        timeout=5,
    )
    assert bad_resp.status_code == 400

    # 2. Valid signature updates payment and order to paid
    secret = os.environ["STRIPE_WEBHOOK_SECRET"]
    sig = _sign_stripe_payload(raw_bytes, secret)
    good_resp = requests.post(
        f"{api_base_url}/api/webhooks/stripe",
        data=raw_bytes,
        headers={"Stripe-Signature": sig, "Content-Type": "application/json"},
        timeout=5,
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["duplicate"] is False

    order_resp = requests.get(f"{api_base_url}/api/orders/{order_id}", headers=customer_headers, timeout=5)
    assert order_resp.status_code == 200
    assert order_resp.json()["status"] == "paid"

    # 3. Replay of same event ID must be safely deduplicated
    dup_resp = requests.post(
        f"{api_base_url}/api/webhooks/stripe",
        data=raw_bytes,
        headers={"Stripe-Signature": sig, "Content-Type": "application/json"},
        timeout=5,
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["duplicate"] is True


def test_razorpay_webhook_signature_and_failure_sync(api_base_url, customer_headers):
    rzp_order_id = f"order_{uuid.uuid4().hex[:10]}"
    order_id, _ = _insert_order_and_payment("razorpay", rzp_order_id)

    payload_dict = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{uuid.uuid4().hex[:10]}",
                    "order_id": rzp_order_id,
                    "status": "failed",
                    "error_description": "OTP authentication failed",
                }
            }
        },
    }
    body_str = json.dumps(payload_dict)

    bad_resp = requests.post(
        f"{api_base_url}/api/webhooks/razorpay",
        data=body_str,
        headers={"X-Razorpay-Signature": "invalid", "Content-Type": "application/json"},
        timeout=5,
    )
    assert bad_resp.status_code == 400

    secret = os.environ["RAZORPAY_WEBHOOK_SECRET"]
    sig = _sign_razorpay_payload(body_str, secret)
    event_id = f"rzp_evt_{uuid.uuid4().hex[:10]}"
    good_resp = requests.post(
        f"{api_base_url}/api/webhooks/razorpay",
        data=body_str,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": event_id,
            "Content-Type": "application/json",
        },
        timeout=5,
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["duplicate"] is False

    order_resp = requests.get(f"{api_base_url}/api/orders/{order_id}", headers=customer_headers, timeout=5)
    assert order_resp.status_code == 200
    assert order_resp.json()["status"] == "failed"


def test_razorpay_webhook_success_and_stripe_webhook_failure(api_base_url, customer_headers):
    # 1. Razorpay payment.captured -> order paid
    rzp_order_id = f"order_cap_{uuid.uuid4().hex[:8]}"
    rzp_oid, _ = _insert_order_and_payment("razorpay", rzp_order_id)
    rzp_body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_cap_{uuid.uuid4().hex[:8]}",
                        "order_id": rzp_order_id,
                        "status": "captured",
                    }
                }
            },
        }
    )
    rzp_sig = _sign_razorpay_payload(rzp_body, os.environ["RAZORPAY_WEBHOOK_SECRET"])
    rzp_resp = requests.post(
        f"{api_base_url}/api/webhooks/razorpay",
        data=rzp_body,
        headers={
            "X-Razorpay-Signature": rzp_sig,
            "X-Razorpay-Event-Id": f"rzp_cap_{uuid.uuid4().hex[:8]}",
            "Content-Type": "application/json",
        },
        timeout=5,
    )
    assert rzp_resp.status_code == 200
    assert requests.get(f"{api_base_url}/api/orders/{rzp_oid}", headers=customer_headers, timeout=5).json()["status"] == "paid"

    # 2. Stripe payment_intent.payment_failed -> order failed
    pi_id = f"pi_fail_{uuid.uuid4().hex[:8]}"
    stripe_oid, _ = _insert_order_and_payment("stripe", pi_id)
    stripe_bytes = json.dumps(
        {
            "id": f"evt_fail_{uuid.uuid4().hex[:8]}",
            "object": "event",
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": pi_id,
                    "object": "payment_intent",
                    "last_payment_error": {"message": "Your card was declined."},
                }
            },
        }
    ).encode("utf-8")
    stripe_sig = _sign_stripe_payload(stripe_bytes, os.environ["STRIPE_WEBHOOK_SECRET"])
    stripe_resp = requests.post(
        f"{api_base_url}/api/webhooks/stripe",
        data=stripe_bytes,
        headers={"Stripe-Signature": stripe_sig, "Content-Type": "application/json"},
        timeout=5,
    )
    assert stripe_resp.status_code == 200
    assert requests.get(f"{api_base_url}/api/orders/{stripe_oid}", headers=customer_headers, timeout=5).json()["status"] == "failed"
