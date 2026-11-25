"""API tests for Admin endpoints and RBAC enforcement."""

import pytest
import requests

pytestmark = pytest.mark.api


def test_admin_endpoints_enforce_rbac(api_base_url, customer_headers, admin_headers):
    for endpoint in ("stats", "orders", "payments", "transactions", "webhooks"):
        cust_resp = requests.get(f"{api_base_url}/api/admin/{endpoint}", headers=customer_headers, timeout=5)
        assert cust_resp.status_code == 403

        admin_resp = requests.get(f"{api_base_url}/api/admin/{endpoint}", headers=admin_headers, timeout=5)
        assert admin_resp.status_code == 200
