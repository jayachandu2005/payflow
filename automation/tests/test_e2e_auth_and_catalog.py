"""E2E UI tests for registration, login, catalog browsing, cart, and checkout form validation."""

import uuid
import pytest
from selenium.webdriver.common.by import By

from automation.pages.auth_page import LoginPage, RegisterPage
from automation.pages.cart_page import CartPage
from automation.pages.checkout_page import CheckoutPage
from automation.pages.products_page import ProductDetailPage, ProductsPage

pytestmark = pytest.mark.e2e


def test_register_browse_cart_and_checkout_validation(driver):
    reg_page = RegisterPage(driver)
    reg_page.open_register()
    email = f"e2e_{uuid.uuid4().hex[:8]}@payflow.dev"
    reg_page.register("E2E Shopper", email, "+14155550199", "Shopper@1234")
    reg_page.screenshot("e2e_registered_catalog")

    products_page = ProductsPage(driver)
    products_page.search_product("FIDO2")
    products_page.open_first_product()

    detail_page = ProductDetailPage(driver)
    assert "FIDO2" in detail_page.get_title()
    detail_page.add_to_cart(quantity=2)
    detail_page.go_to_cart()

    cart_page = CartPage(driver)
    cart_page.proceed_to_checkout()

    checkout_page = CheckoutPage(driver)
    # Negative test: invalid phone number triggers backend validation error
    checkout_page.fill_customer_info(
        name="E2E Shopper",
        email=email,
        phone="123",
        address="221B Baker Street",
        city="London",
        postal_code="NW16XE",
        country="United Kingdom",
    )
    checkout_page.click(checkout_page.SUBMIT_BTN)
    err_text = checkout_page.wait_visible(checkout_page.ERROR_ALERT).text
    assert "7 characters" in err_text or "7 digits" in err_text or "customer_phone" in err_text
    checkout_page.screenshot("e2e_checkout_validation_error")


def test_user_and_admin_dashboards_render(driver):
    login_page = LoginPage(driver)
    login_page.open_login()
    login_page.login("admin@payflow.dev", "Admin@123")
    login_page.wait_url_contains("/admin")
    admin_dash = login_page.wait_visible((By.CSS_SELECTOR, "[data-testid='admin-dashboard']"))
    assert "Admin Operations Dashboard" in admin_dash.text
    login_page.screenshot("e2e_admin_dashboard")

    login_page.open("/dashboard")
    user_dash = login_page.wait_visible((By.CSS_SELECTOR, "[data-testid='user-dashboard']"))
    assert "Customer Dashboard" in user_dash.text
    login_page.screenshot("e2e_user_dashboard")


def test_invalid_login_shows_error(driver):
    login_page = LoginPage(driver)
    login_page.open_login()
    err = login_page.attempt_invalid_login("customer@payflow.dev", "WrongPass999!")
    assert "Invalid email or password" in err
    login_page.screenshot("e2e_invalid_login")

    # Verify Home page renders cleanly too
    login_page.open("/")
    hero = login_page.wait_visible((By.CSS_SELECTOR, "[data-testid='home-hero']"))
    assert "PayFlow" in hero.text or "Payment" in hero.text
