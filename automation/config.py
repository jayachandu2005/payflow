"""Configuration and official sandbox test data for Selenium E2E automation."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173").rstrip("/")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8000").rstrip("/")
HEADLESS = os.getenv("E2E_HEADLESS", "false").strip().lower() == "true"
RECORD_VIDEO = os.getenv("E2E_RECORD_VIDEO", "true").strip().lower() == "true"
BROWSER = os.getenv("E2E_BROWSER", "chrome").strip().lower()
DEFAULT_TIMEOUT = int(os.getenv("E2E_TIMEOUT", "20"))
GATEWAY_TIMEOUT = int(os.getenv("E2E_GATEWAY_TIMEOUT", "35"))
PREFERRED_GATEWAY = os.getenv("E2E_DEFAULT_GATEWAY", "auto").strip().lower()

SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

for directory in (SCREENSHOTS_DIR, RECORDINGS_DIR, LOGS_DIR, REPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Official Razorpay Test Credentials (https://razorpay.com/docs/payments/payments/test-card-details/)
RAZORPAY_TEST_CARD = {
    "number": os.getenv("RZP_TEST_CARD_NUMBER", "4100280000001007"),
    "expiry": os.getenv("RZP_TEST_CARD_EXPIRY", "12/30"),
    "cvv": os.getenv("RZP_TEST_CARD_CVV", "123"),
    "name": "Alex Mercer",
    "otp_success": "123456",
    "otp_fail": "123",
}

# Official Stripe Sandbox 3DS2 Test Cards (https://docs.stripe.com/testing#regulatory-cards)
STRIPE_TEST_CARDS = {
    "3ds_success": os.getenv("STRIPE_3DS_SUCCESS_CARD", "4000002500003155"),
    "3ds_fail": os.getenv("STRIPE_3DS_FAIL_CARD", "4000000000003063"),
    "declined": os.getenv("STRIPE_DECLINED_CARD", "4000000000000002"),
    "expiry": "12/30",
    "cvc": "123",
    "postal": "94105",
}
