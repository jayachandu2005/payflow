"""Order History Page Object."""

from selenium.webdriver.common.by import By

from automation.pages.base_page import BasePage


class OrdersPage(BasePage):
    ORDERS_TABLE = (By.CSS_SELECTOR, "[data-testid='orders-table']")

    def open_orders(self) -> None:
        self.open("/orders")
        self.wait_visible(self.ORDERS_TABLE)

    def assert_order_present_with_status(self, order_number: str, expected_status: str) -> None:
        self.wait_visible(self.ORDERS_TABLE)
        row_xpath = f"//tr[contains(., '{order_number}') and contains(., '{expected_status}')]"
        self.wait_visible((By.XPATH, row_xpath))
        self.screenshot(f"order_history_{expected_status}")
