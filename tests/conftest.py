"""Shared fixtures for PayFlow Python Requests API tests."""

import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def api_base_url():
    """Spin up an isolated FastAPI + Uvicorn server with a dedicated test SQLite database."""
    test_db_path = PROJECT_ROOT / "database" / "test_api.db"
    if test_db_path.exists():
        test_db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key-for-api-suite-minimum-32-bytes"
    # Provide deterministic webhook secrets for cryptographic signature tests if not already set
    if not os.environ.get("STRIPE_WEBHOOK_SECRET") or "replace_with" in os.environ.get("STRIPE_WEBHOOK_SECRET", ""):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_api_stripe_webhook_secret_12345"
    if not os.environ.get("RAZORPAY_WEBHOOK_SECRET") or "replace_with" in os.environ.get("RAZORPAY_WEBHOOK_SECRET", ""):
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_test_api_webhook_secret_12345"

    # Clear cached settings so test environment variables take effect
    from app.config import get_settings
    get_settings.cache_clear()

    from app.database import init_db, SessionLocal
    from app.seed import seed_database
    from app.main import app

    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    port = _find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/api/health", timeout=1)
            if r.status_code == 200:
                break
        except requests.RequestException:
            time.sleep(0.1)
    else:
        raise RuntimeError("Test Uvicorn server failed to become healthy")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except OSError:
            pass


@pytest.fixture()
def customer_headers(api_base_url):
    """Authenticate as seeded customer and return Authorization headers."""
    resp = requests.post(
        f"{api_base_url}/api/auth/login",
        json={"email": "customer@payflow.dev", "password": "Customer@123"},
        timeout=5,
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(api_base_url):
    """Authenticate as seeded admin and return Authorization headers."""
    resp = requests.post(
        f"{api_base_url}/api/auth/login",
        json={"email": "admin@payflow.dev", "password": "Admin@123"},
        timeout=5,
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
