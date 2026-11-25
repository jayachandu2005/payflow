"""Pytest fixtures for Chrome WebDriver setup, video recording, and failure evidence."""

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from automation.config import API_URL, BROWSER, HEADLESS, PREFERRED_GATEWAY, RECORD_VIDEO
from automation.utils.logger import get_logger
from automation.utils.recorder import BrowserVideoRecorder
from automation.utils.screenshots import capture_screenshot

logger = get_logger("payflow.conftest")


def _create_driver():
    if BROWSER == "edge":
        from selenium.webdriver.edge.options import Options as EdgeOptions

        opts = EdgeOptions()
        if HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1440,900")
        return webdriver.Edge(options=opts)

    opts = ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception:
        from webdriver_manager.chrome import ChromeDriverManager

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
    try:
        driver.execute_cdp_cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})
    except Exception:
        pass
    return driver


@pytest.fixture()
def driver(request):
    """Provide a fresh WebDriver instance per test with automatic MP4 video recording."""
    web_driver = _create_driver()
    web_driver.implicitly_wait(0)
    recorder = BrowserVideoRecorder(web_driver, request.node.name) if RECORD_VIDEO else None
    if recorder:
        recorder.start()

    yield web_driver

    rep_setup = getattr(request.node, "rep_setup", None)
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call and rep_call.failed:
        try:
            capture_screenshot(web_driver, f"FAIL_{request.node.name}")
        except Exception as exc:
            logger.warning("Failed to capture failure screenshot: %s", exc)

    if recorder:
        recorded_path = recorder.stop()
        # Remove empty/stub videos for skipped tests
        if recorded_path and ((rep_call and rep_call.skipped) or (rep_setup and rep_setup.skipped)):
            recorded_path.unlink(missing_ok=True)
    web_driver.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session")
def active_gateway_config():
    """Query backend /api/payments/config to discover configured live sandbox gateways."""
    try:
        resp = requests.get(f"{API_URL}/api/payments/config", timeout=5)
        resp.raise_for_status()
        cfg = resp.json()
    except Exception as exc:
        pytest.skip(f"Backend not reachable at {API_URL}: {exc}")
        return {}

    selected = PREFERRED_GATEWAY
    if selected == "auto":
        if cfg.get("razorpay_configured"):
            selected = "razorpay"
        elif cfg.get("stripe_configured"):
            selected = "stripe"
        else:
            selected = "none"
    cfg["selected_gateway"] = selected
    return cfg
