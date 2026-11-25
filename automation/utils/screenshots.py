"""Screenshot capture utility saving PNG evidence into screenshots/."""

from datetime import datetime, timezone
from pathlib import Path

from selenium.webdriver.remote.webdriver import WebDriver

from automation.config import SCREENSHOTS_DIR
from automation.utils.logger import get_logger

logger = get_logger("payflow.screenshots")


def capture_screenshot(driver: WebDriver, name: str) -> Path:
    """Capture and save a PNG screenshot from the active WebDriver window."""
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = SCREENSHOTS_DIR / f"{ts}_{safe_name}.png"
    driver.save_screenshot(str(target))
    logger.info("Saved screenshot: %s", target)
    return target
