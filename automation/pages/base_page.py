"""Base Page Object providing explicit waits, safe actions, and screenshot helpers."""

from pathlib import Path
from typing import Tuple

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from automation.config import BASE_URL, DEFAULT_TIMEOUT
from automation.utils.logger import get_logger
from automation.utils.screenshots import capture_screenshot


class BasePage:
    """Reusable base class for all PayFlow Page Objects."""

    def __init__(self, driver: WebDriver, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
        self.logger = get_logger(self.__class__.__name__)

    def open(self, path: str = "/") -> None:
        url = f"{BASE_URL}{path}" if path.startswith("/") else path
        self.logger.info("Navigating to %s", url)
        self.driver.get(url)

    def wait_visible(self, locator: Tuple[str, str], timeout: int | None = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.visibility_of_element_located(locator))

    def wait_clickable(self, locator: Tuple[str, str], timeout: int | None = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.element_to_be_clickable(locator))

    def wait_present(self, locator: Tuple[str, str], timeout: int | None = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.presence_of_element_located(locator))

    def wait_url_contains(self, fragment: str, timeout: int | None = None) -> None:
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        wait.until(EC.url_contains(fragment))

    def click(self, locator: Tuple[str, str], timeout: int | None = None) -> None:
        elem = self.wait_clickable(locator, timeout=timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'nearest', inline: 'nearest'});", elem)
        elem.click()

    def js_click(self, locator: Tuple[str, str], timeout: int | None = None) -> None:
        elem = self.wait_clickable(locator, timeout=timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'nearest', inline: 'nearest'});", elem)
        self.driver.execute_script("arguments[0].click();", elem)

    def type_text(self, locator: Tuple[str, str], text: str, clear: bool = True) -> None:
        elem = self.wait_visible(locator)
        if clear:
            elem.send_keys(Keys.CONTROL, "a")
            elem.send_keys(Keys.BACK_SPACE)
            if elem.get_attribute("value"):
                elem.clear()
        elem.send_keys(text)

    def screenshot(self, label: str) -> Path:
        return capture_screenshot(self.driver, label)
