"""Negative E2E tests for failed OTP/3DS authentication, declined card, and payment cancellation."""

import pytest

from automation.config import RAZORPAY_TEST_CARD, STRIPE_TEST_CARDS
from automation.pages.auth_page import LoginPage
from automation.pages.cart_page import CartPage
from automation.pages.checkout_page import CheckoutPage
from automation.pages.orders_page import OrdersPage
from automation.pages.payment_page import PaymentPage
from automation.pages.products_page import ProductDetailPage, ProductsPage
from automation.pages.result_page import PaymentResultPage

pytestmark = [pytest.mark.e2e, pytest.mark.negative]


def _setup_checkout_to_payment(driver, provider: str, payment_method: str):
    login_page = LoginPage(driver)
    login_page.open_login()
    login_page.login("customer@payflow.dev", "Customer@123")

    products_page = ProductsPage(driver)
    products_page.open_catalog()
    products_page.open_first_product()

    detail_page = ProductDetailPage(driver)
    detail_page.add_to_cart(quantity=1)
    detail_page.go_to_cart()

    cart_page = CartPage(driver)
    cart_page.proceed_to_checkout()

    checkout_page = CheckoutPage(driver)
    checkout_page.fill_customer_info(
        name="Alex Mercer",
        email="customer@payflow.dev",
        phone="+14155550101",
        address="500 Market Street",
        city="San Francisco",
        postal_code="94105",
        country="United States",
    )
    checkout_page.select_payment_method(provider, payment_method)
    checkout_page.submit_checkout()


@pytest.mark.gateway_live
def test_failed_otp_or_3ds_authentication(driver, active_gateway_config):
    gateway = active_gateway_config.get("selected_gateway")
    if gateway == "none":
        pytest.skip("No live sandbox payment gateway keys configured in .env.")

    method = "razorpay_checkout" if gateway == "razorpay" else "card"
    _setup_checkout_to_payment(driver, gateway, method)

    payment_page = PaymentPage(driver)
    order_number = payment_page.wait_ready()

    if gateway == "razorpay":
        payment_page.complete_razorpay_card_otp(otp=RAZORPAY_TEST_CARD["otp_fail"], expect_success=False)
    else:
        payment_page.complete_stripe_card_3ds(
            card_number=STRIPE_TEST_CARDS["3ds_fail"],
            complete_challenge=False,
            expect_challenge=True,
        )

    result_page = PaymentResultPage(driver)
    final_status = result_page.wait_for_failure_or_cancelled()
    assert final_status in ("failed", "cancelled")

    result_page.go_to_order_history()
    orders_page = OrdersPage(driver)
    orders_page.assert_order_present_with_status(order_number, final_status)


@pytest.mark.gateway_live
def test_user_cancels_payment_before_completion(driver, active_gateway_config):
    gateway = active_gateway_config.get("selected_gateway")
    if gateway == "none":
        pytest.skip("No live sandbox payment gateway keys configured in .env.")

    method = "razorpay_checkout" if gateway == "razorpay" else "card"
    _setup_checkout_to_payment(driver, gateway, method)

    payment_page = PaymentPage(driver)
    order_number = payment_page.wait_ready()
    payment_page.cancel_payment()

    result_page = PaymentResultPage(driver)
    final_status = result_page.wait_for_failure_or_cancelled()
    assert final_status == "cancelled"

    result_page.go_to_order_history()
    orders_page = OrdersPage(driver)
    orders_page.assert_order_present_with_status(order_number, "cancelled")
