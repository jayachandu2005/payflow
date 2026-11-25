"""API tests for user registration, login, JWT validation, and RBAC."""

import uuid
import pytest
import requests

pytestmark = pytest.mark.api


def test_health_endpoint(api_base_url):
    resp = requests.get(f"{api_base_url}/api/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_register_login_and_me_flow(api_base_url):
    email = f"qa_{uuid.uuid4().hex[:8]}@payflow.dev"
    reg_resp = requests.post(
        f"{api_base_url}/api/auth/register",
        json={
            "email": email,
            "full_name": "QA Test User",
            "phone": "+14155550111",
            "password": "StrongPassword@1",
        },
        timeout=5,
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email
    assert reg_data["user"]["role"] == "customer"

    # Duplicate email must return 409 Conflict
    dup_resp = requests.post(
        f"{api_base_url}/api/auth/register",
        json={
            "email": email,
            "full_name": "QA Test User",
            "password": "StrongPassword@1",
        },
        timeout=5,
    )
    assert dup_resp.status_code == 409

    # Login
    login_resp = requests.post(
        f"{api_base_url}/api/auth/login",
        json={"email": email, "password": "StrongPassword@1"},
        timeout=5,
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Profile endpoint
    me_resp = requests.get(
        f"{api_base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_auth_invalid_cases(api_base_url):
    # Weak password rejected with 422
    weak_resp = requests.post(
        f"{api_base_url}/api/auth/register",
        json={"email": "weak@payflow.dev", "full_name": "Weak", "password": "123"},
        timeout=5,
    )
    assert weak_resp.status_code == 422

    # Wrong password rejected with 401
    bad_login = requests.post(
        f"{api_base_url}/api/auth/login",
        json={"email": "customer@payflow.dev", "password": "WrongPassword"},
        timeout=5,
    )
    assert bad_login.status_code == 401

    # Unauthenticated /me rejected with 401
    unauth = requests.get(f"{api_base_url}/api/auth/me", timeout=5)
    assert unauth.status_code == 401
