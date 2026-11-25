"""Payment Processing Page Object supporting live Stripe 3DS2 & Razorpay OTP sandboxes."""

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from automation.config import GATEWAY_TIMEOUT, RAZORPAY_TEST_CARD, STRIPE_TEST_CARDS
from automation.pages.base_page import BasePage


class PaymentPage(BasePage):
    ORDER_NUMBER = (By.CSS_SELECTOR, "[data-testid='payment-order-number']")
    GATEWAY_PANEL = (By.CSS_SELECTOR, "[data-testid='payment-gateway-panel']")
    CANCEL_BTN = (By.CSS_SELECTOR, "[data-testid='payment-cancel-btn']")

    # Razorpay controls
    LAUNCH_RAZORPAY_BTN = (By.CSS_SELECTOR, "[data-testid='launch-razorpay-btn']")
    RAZORPAY_IFRAME = (By.CSS_SELECTOR, "iframe.razorpay-checkout-frame")

    # Stripe Elements controls
    STRIPE_CARD_IFRAME = (By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']")
    STRIPE_PAY_BTN = (By.CSS_SELECTOR, "[data-testid='stripe-pay-submit']")
    STRIPE_3DS_IFRAME = (By.CSS_SELECTOR, "iframe[src*='hooks.stripe.com'], iframe[name*='stripe-challenge']")

    def wait_ready(self) -> str:
        self.wait_visible(self.GATEWAY_PANEL)
        return self.wait_visible(self.ORDER_NUMBER).text

    def cancel_payment(self) -> None:
        self.click(self.CANCEL_BTN)
        self.wait_url_contains("/payment/result/")

    def complete_razorpay_card_otp(self, otp: str = RAZORPAY_TEST_CARD["otp_success"], expect_success: bool = True) -> None:
        """Interact with genuine Razorpay Checkout iframe and simulated ACS Bank OTP window."""
        self.click(self.LAUNCH_RAZORPAY_BTN)

        iframe = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.presence_of_element_located(self.RAZORPAY_IFRAME)
        )
        self.driver.switch_to.frame(iframe)
        self.screenshot("razorpay_checkout_opened")

        # Select Card payment method inside Razorpay Checkout
        card_method = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Card') or @data-value='card'] | //div[contains(@data-testid, 'card')]"))
        )
        card_method.click()

        card_num_input = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='card[number]'], input[placeholder*='Card Number']"))
        )
        card_num_input.send_keys(RAZORPAY_TEST_CARD["number"])

        expiry_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='card[expiry]'], input[placeholder*='MM']")
        expiry_input.send_keys(RAZORPAY_TEST_CARD["expiry"])

        cvv_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='card[cvv]'], input[placeholder*='CVV']")
        cvv_input.send_keys(RAZORPAY_TEST_CARD["cvv"])

        try:
            name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='card[name]'], input[placeholder*='Name']")
            if not name_input.get_attribute("value"):
                name_input.send_keys(RAZORPAY_TEST_CARD["name"])
        except Exception:
            pass

        pay_btn = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], button[data-testid='pay-cta']"))
        )
        pay_btn.click()

        # Switch back to top context and handle Razorpay Bank ACS OTP popup/iframe
        self.driver.switch_to.default_content()
        main_handle = self.driver.current_window_handle

        WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(lambda d: len(d.window_handles) > 1 or self._find_otp_input(d) is not None)
        if len(self.driver.window_handles) > 1:
            for handle in self.driver.window_handles:
                if handle != main_handle:
                    self.driver.switch_to.window(handle)
                    break

        otp_input = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(lambda d: self._find_otp_input(d))
        self.screenshot("razorpay_otp_page")
        otp_input.clear()
        otp_input.send_keys(otp)

        submit_otp_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], #submit-action")
        submit_otp_btn.click()

        self.driver.switch_to.window(main_handle)
        self.wait_url_contains("/payment/result/", timeout=GATEWAY_TIMEOUT)

    @staticmethod
    def _find_otp_input(driver):
        selectors = [
            "input[type='password']",
            "input[name*='otp' i]",
            "input[id*='otp' i]",
            "input[placeholder*='OTP' i]",
            "#otp",
        ]
        for sel in selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems and elems[0].is_displayed():
                return elems[0]
        return None

    def complete_stripe_card_3ds(
        self,
        card_number: str = STRIPE_TEST_CARDS["3ds_success"],
        complete_challenge: bool = True,
        expect_challenge: bool = True,
    ) -> None:
        """Enter official Stripe test card into Stripe Elements and interact with genuine 3DS2 modal."""
        card_iframe = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.presence_of_element_located(self.STRIPE_CARD_IFRAME)
        )
        self.driver.switch_to.frame(card_iframe)

        # Stripe CardElement renders card number, exp, cvc, postal inside one secure iframe
        card_input = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[autocomplete='cc-number']"))
        )
        card_input.send_keys(card_number)

        exp_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='exp-date'], input[autocomplete='cc-exp']")
        exp_input.send_keys(STRIPE_TEST_CARDS["expiry"])

        cvc_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='cvc'], input[autocomplete='cc-csc']")
        cvc_input.send_keys(STRIPE_TEST_CARDS["cvc"])

        postal_elems = self.driver.find_elements(By.CSS_SELECTOR, "input[name='postal'], input[autocomplete='postal-code']")
        if postal_elems:
            postal_elems[0].send_keys(STRIPE_TEST_CARDS["postal"])

        self.driver.switch_to.default_content()
        self.screenshot("stripe_card_entered")
        self.click(self.STRIPE_PAY_BTN)

        if expect_challenge:
            self._handle_stripe_3ds_challenge(complete=complete_challenge)

        self.wait_url_contains("/payment/result/", timeout=GATEWAY_TIMEOUT)

    def _handle_stripe_3ds_challenge(self, complete: bool = True) -> None:
        """Locate nested Stripe 3DS2 challenge iframe and click Complete or Fail authentication."""
        try:
            outer_iframe = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame'][src*='three_ds'], iframe[src*='hooks.stripe.com']"))
            )
            self.driver.switch_to.frame(outer_iframe)
        except TimeoutException:
            # Stripe may nest the 3DS challenge inside a full-page challenge frame
            for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
                src = frame.get_attribute("src") or ""
                if "stripe" in src and ("3ds" in src or "challenge" in src or "hooks" in src):
                    self.driver.switch_to.frame(frame)
                    break

        # Check for nested challengeFrame inside Stripe's 3DS container
        nested = self.driver.find_elements(By.CSS_SELECTOR, "iframe#challengeFrame, iframe[name='acsFrame'], iframe")
        for nframe in nested:
            src = nframe.get_attribute("src") or ""
            if "hooks.stripe.com" in src or "challenge" in src or nframe.get_attribute("id") == "challengeFrame":
                self.driver.switch_to.frame(nframe)
                break

        btn_locator = (
            (By.CSS_SELECTOR, "#test-source-authorize-3ds, button[id*='complete' i], button[value='complete']")
            if complete
            else (By.CSS_SELECTOR, "#test-source-fail-3ds, button[id*='fail' i], button[value='fail']")
        )
        try:
            challenge_btn = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(EC.element_to_be_clickable(btn_locator))
        except TimeoutException:
            xpath = "//button[contains(., 'Complete')]" if complete else "//button[contains(., 'Fail')]"
            challenge_btn = WebDriverWait(self.driver, GATEWAY_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, xpath)))

        self.screenshot("stripe_3ds2_challenge_page")
        challenge_btn.click()
        self.driver.switch_to.default_content()
