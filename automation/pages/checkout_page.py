"""Checkout Page Object covering customer form and gateway method selection."""

from selenium.webdriver.common.by import By

from automation.pages.base_page import BasePage


class CheckoutPage(BasePage):
    NAME_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-name']")
    EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-email']")
    PHONE_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-phone']")
    COUNTRY_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-country']")
    ADDRESS_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-address']")
    CITY_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-city']")
    POSTAL_INPUT = (By.CSS_SELECTOR, "[data-testid='checkout-postal']")
    SUBMIT_BTN = (By.CSS_SELECTOR, "[data-testid='checkout-submit']")
    ERROR_ALERT = (By.CSS_SELECTOR, "[data-testid='checkout-error']")

    def fill_customer_info(
        self,
        name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        postal_code: str,
        country: str = "United States",
    ) -> None:
        self.type_text(self.NAME_INPUT, name)
        self.type_text(self.EMAIL_INPUT, email)
        self.type_text(self.PHONE_INPUT, phone)
        self.type_text(self.COUNTRY_INPUT, country)
        self.type_text(self.ADDRESS_INPUT, address)
        self.type_text(self.CITY_INPUT, city)
        self.type_text(self.POSTAL_INPUT, postal_code)

    def select_payment_method(self, provider: str, payment_method: str) -> None:
        locator = (By.CSS_SELECTOR, f"[data-testid='method-{provider}-{payment_method}']")
        self.click(locator)

    def submit_checkout(self) -> None:
        self.screenshot("checkout_filled")
        self.js_click(self.SUBMIT_BTN)
        self.wait_url_contains("/payment/process/")
