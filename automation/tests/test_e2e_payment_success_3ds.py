"""E2E test verifying complete Product -> Cart -> Checkout -> Real OTP/3DS -> Verified Success."""

import pytest

from automation.config import RAZORPAY_TEST_CARD, STRIPE_TEST_CARDS
from automation.pages.auth_page import LoginPage
from automation.pages.cart_page import CartPage
from automation.pages.checkout_page import CheckoutPage
from automation.pages.orders_page import OrdersPage
from automation.pages.payment_page import PaymentPage
from automation.pages.products_page import ProductDetailPage, ProductsPage
from automation.pages.result_page import PaymentResultPage

pytestmark = [pytest.mark.e2e, pytest.mark.gateway_live]


def test_complete_sandbox_payment_with_real_otp_or_3ds(driver, active_gateway_config):
    gateway = active_gateway_config.get("selected_gateway")
    if gateway == "none":
        pytest.skip("No live sandbox payment gateway keys configured in .env (STRIPE_* or RAZORPAY_*).")

    # 1. Login
    login_page = LoginPage(driver)
    login_page.open_login()
    login_page.login("customer@payflow.dev", "Customer@123")

    # 2. Select product & add to cart
    products_page = ProductsPage(driver)
    products_page.open_catalog()
    products_page.open_first_product()

    detail_page = ProductDetailPage(driver)
    detail_page.add_to_cart(quantity=1)
    detail_page.go_to_cart()

    # 3. Proceed to checkout
    cart_page = CartPage(driver)
    cart_page.proceed_to_checkout()

    # 4. Fill customer info & choose configured gateway
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
    if gateway == "razorpay":
        checkout_page.select_payment_method("razorpay", "razorpay_checkout")
    else:
        checkout_page.select_payment_method("stripe", "card")
    checkout_page.submit_checkout()

    # 5. Complete real gateway interface + genuine OTP / 3DS2 challenge
    payment_page = PaymentPage(driver)
    order_number = payment_page.wait_ready()
    if gateway == "razorpay":
        payment_page.complete_razorpay_card_otp(otp=RAZORPAY_TEST_CARD["otp_success"], expect_success=True)
    else:
        payment_page.complete_stripe_card_3ds(
            card_number=STRIPE_TEST_CARDS["3ds_success"],
            complete_challenge=True,
            expect_challenge=True,
        )

    # 6. Verify authoritative payment success & order status
    result_page = PaymentResultPage(driver)
    verified_order_num = result_page.wait_for_success()
    assert verified_order_num == order_number
    assert result_page.get_order_status() == "paid"

    # 7. Verify order status persisted in Order History
    result_page.go_to_order_history()
    orders_page = OrdersPage(driver)
    orders_page.assert_order_present_with_status(order_number, "paid")
