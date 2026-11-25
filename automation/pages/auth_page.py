"""Authentication Page Objects (Login and Registration)."""

from selenium.webdriver.common.by import By

from automation.pages.base_page import BasePage


class LoginPage(BasePage):
    EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='login-email']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='login-password']")
    SUBMIT_BTN = (By.CSS_SELECTOR, "[data-testid='login-submit']")
    ERROR_ALERT = (By.CSS_SELECTOR, "[data-testid='login-error']")
    NAV_USER_EMAIL = (By.CSS_SELECTOR, "[data-testid='nav-user-email']")

    def open_login(self) -> None:
        self.open("/login")
        self.wait_visible(self.EMAIL_INPUT)

    def login(self, email: str, password: str) -> None:
        self.type_text(self.EMAIL_INPUT, email)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.SUBMIT_BTN)
        self.wait_visible(self.NAV_USER_EMAIL)

    def attempt_invalid_login(self, email: str, password: str) -> str:
        self.type_text(self.EMAIL_INPUT, email)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.SUBMIT_BTN)
        return self.wait_visible(self.ERROR_ALERT).text


class RegisterPage(BasePage):
    NAME_INPUT = (By.CSS_SELECTOR, "[data-testid='register-name']")
    EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='register-email']")
    PHONE_INPUT = (By.CSS_SELECTOR, "[data-testid='register-phone']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-password']")
    SUBMIT_BTN = (By.CSS_SELECTOR, "[data-testid='register-submit']")
    NAV_USER_EMAIL = (By.CSS_SELECTOR, "[data-testid='nav-user-email']")

    def open_register(self) -> None:
        self.open("/register")
        self.wait_visible(self.NAME_INPUT)

    def register(self, full_name: str, email: str, phone: str, password: str) -> None:
        self.type_text(self.NAME_INPUT, full_name)
        self.type_text(self.EMAIL_INPUT, email)
        self.type_text(self.PHONE_INPUT, phone)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.SUBMIT_BTN)
        self.wait_visible(self.NAV_USER_EMAIL)
