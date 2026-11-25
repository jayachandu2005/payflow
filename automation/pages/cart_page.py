"""Shopping Cart Page Object."""

from selenium.webdriver.common.by import By

from automation.pages.base_page import BasePage


class CartPage(BasePage):
    SUMMARY_CARD = (By.CSS_SELECTOR, "[data-testid='cart-summary']")
    TOTAL_TEXT = (By.CSS_SELECTOR, "[data-testid='cart-total']")
    PROCEED_BTN = (By.CSS_SELECTOR, "[data-testid='proceed-to-checkout']")
    EMPTY_STATE = (By.CSS_SELECTOR, "[data-testid='cart-empty']")
    CLEAR_BTN = (By.CSS_SELECTOR, "[data-testid='cart-clear']")

    def open_cart(self) -> None:
        self.open("/cart")

    def proceed_to_checkout(self) -> None:
        self.wait_visible(self.SUMMARY_CARD)
        self.screenshot("cart_summary")
        self.click(self.PROCEED_BTN)
        self.wait_url_contains("/checkout")
