"""Payment Result Page Object."""

from selenium.webdriver.common.by import By

from automation.config import GATEWAY_TIMEOUT
from automation.pages.base_page import BasePage


class PaymentResultPage(BasePage):
    RESULT_CARD = (By.CSS_SELECTOR, "[data-testid='payment-result-card']")
    SUCCESS_BANNER = (By.CSS_SELECTOR, "[data-testid='result-status-success']")
    FAILED_BANNER = (By.CSS_SELECTOR, "[data-testid='result-status-failed']")
    PENDING_BANNER = (By.CSS_SELECTOR, "[data-testid='result-status-pending']")
    ORDER_NUMBER = (By.CSS_SELECTOR, "[data-testid='result-order-number']")
    ORDER_STATUS = (By.CSS_SELECTOR, "[data-testid='result-order-status']")
    VIEW_ORDERS_BTN = (By.CSS_SELECTOR, "[data-testid='result-view-orders']")

    def wait_for_success(self) -> str:
        self.wait_visible(self.SUCCESS_BANNER, timeout=GATEWAY_TIMEOUT)
        self.screenshot("payment_result_success")
        return self.wait_visible(self.ORDER_NUMBER).text

    def wait_for_failure_or_cancelled(self) -> str:
        self.wait_visible(self.FAILED_BANNER, timeout=GATEWAY_TIMEOUT)
        self.screenshot("payment_result_failed")
        return self.wait_visible(self.ORDER_STATUS).text.strip().lower()

    def get_order_status(self) -> str:
        return self.wait_visible(self.ORDER_STATUS).text.strip().lower()

    def go_to_order_history(self) -> None:
        self.js_click(self.VIEW_ORDERS_BTN)
        self.wait_url_contains("/orders")
