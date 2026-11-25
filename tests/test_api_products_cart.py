"""API tests for product catalog and persistent shopping cart operations."""

import uuid
import pytest
import requests

pytestmark = pytest.mark.api


def test_list_and_filter_products(api_base_url):
    resp = requests.get(f"{api_base_url}/api/products", timeout=5)
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) >= 6

    search_resp = requests.get(f"{api_base_url}/api/products?search=FIDO2", timeout=5)
    assert search_resp.status_code == 200
    assert any("FIDO2" in p["name"] for p in search_resp.json())

    not_found = requests.get(f"{api_base_url}/api/products/999999", timeout=5)
    assert not_found.status_code == 404


def test_product_creation_requires_admin(api_base_url, customer_headers, admin_headers):
    payload = {
        "name": "API Created Hardware Token",
        "slug": f"api-token-{uuid.uuid4().hex[:6]}",
        "description": "High assurance cryptographic security module for API tests.",
        "price_cents": 5900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1614064641938-3bbee52942c7",
        "category": "Security Hardware",
        "stock": 20,
    }
    forbidden = requests.post(f"{api_base_url}/api/products", json=payload, headers=customer_headers, timeout=5)
    assert forbidden.status_code == 403

    created = requests.post(f"{api_base_url}/api/products", json=payload, headers=admin_headers, timeout=5)
    assert created.status_code == 201
    assert created.json()["slug"] == payload["slug"]


def test_cart_lifecycle(api_base_url, customer_headers):
    # Clear cart first
    requests.delete(f"{api_base_url}/api/cart", headers=customer_headers, timeout=5)

    products = requests.get(f"{api_base_url}/api/products", timeout=5).json()
    first_product = products[0]

    add_resp = requests.post(
        f"{api_base_url}/api/cart/items",
        json={"product_id": first_product["id"], "quantity": 2},
        headers=customer_headers,
        timeout=5,
    )
    assert add_resp.status_code == 201
    cart = add_resp.json()
    assert cart["item_count"] == 2
    assert cart["subtotal_cents"] == first_product["price_cents"] * 2
    item_id = cart["items"][0]["id"]

    # Update quantity
    patch_resp = requests.patch(
        f"{api_base_url}/api/cart/items/{item_id}",
        json={"quantity": 3},
        headers=customer_headers,
        timeout=5,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["item_count"] == 3

    # Remove item
    del_resp = requests.delete(
        f"{api_base_url}/api/cart/items/{item_id}",
        headers=customer_headers,
        timeout=5,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["item_count"] == 0
