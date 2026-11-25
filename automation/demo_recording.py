"""Automated demo walkthrough recording Login -> Products -> Cart -> Checkout -> Razorpay Checkout -> Reports."""

import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.utils.recorder import BrowserVideoRecorder  # noqa: E402

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5179").rstrip("/")
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def run_demo() -> None:
    opts = Options()
    if os.getenv("E2E_HEADLESS", "true").lower() == "true":
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 20)
    recorder = BrowserVideoRecorder(driver, "payflow_demo_walkthrough", fps=4)
    target_mp4 = EVIDENCE_DIR / "payflow_demo_walkthrough.mp4"
    recorder.output_path = target_mp4
    recorder.start()

    try:
        # 1. Home page
        driver.get(f"{BASE_URL}/")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='home-hero']")))
        time.sleep(1.0)

        # 2. Login
        driver.get(f"{BASE_URL}/login")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='login-email']"))).send_keys(
            "customer@payflow.dev"
        )
        driver.find_element(By.CSS_SELECTOR, "[data-testid='login-password']").send_keys("Customer@123")
        driver.find_element(By.CSS_SELECTOR, "[data-testid='login-submit']").click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='nav-user-email']")))
        time.sleep(1.0)

        # 3. Product Catalog & Search
        driver.get(f"{BASE_URL}/products")
        search = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='products-search']")))
        search.send_keys("FIDO2")
        details_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid^='product-details-']")))
        time.sleep(0.8)
        driver.execute_script("arguments[0].click();", details_btn)
        wait.until(EC.url_contains("/products/"))
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='product-detail-title']")))
        time.sleep(1.0)

        # 4. Add to Cart & Cart page
        add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='detail-add-to-cart']")))
        driver.execute_script("arguments[0].click();", add_btn)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='detail-added-alert']")))
        time.sleep(0.8)
        driver.get(f"{BASE_URL}/cart")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='cart-summary']")))
        time.sleep(1.0)

        # 5. Checkout & Customer Form + Razorpay Selection
        proceed_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='proceed-to-checkout']")))
        driver.execute_script("arguments[0].click();", proceed_btn)
        wait.until(EC.url_contains("/checkout"))
        phone = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='checkout-phone']")))
        phone.clear()
        phone.send_keys("+14155550101")
        addr = driver.find_element(By.CSS_SELECTOR, "[data-testid='checkout-address']")
        addr.clear()
        addr.send_keys("500 Market Street")
        city = driver.find_element(By.CSS_SELECTOR, "[data-testid='checkout-city']")
        city.clear()
        city.send_keys("San Francisco")
        postal = driver.find_element(By.CSS_SELECTOR, "[data-testid='checkout-postal']")
        postal.clear()
        postal.send_keys("94105")
        rzp_opt = driver.find_element(By.CSS_SELECTOR, "[data-testid='method-razorpay-razorpay_checkout']")
        rzp_opt.click()
        time.sleep(1.0)
        driver.find_element(By.CSS_SELECTOR, "[data-testid='checkout-submit']").click()

        # 6. Payment Processing Page (Genuine Razorpay Sandbox Order + Checkout Modal)
        wait.until(EC.url_contains("/payment/process/"))
        launch_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='launch-razorpay-btn']")))
        time.sleep(1.0)
        launch_btn.click()
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.razorpay-checkout-frame")))
            time.sleep(2.5)
        except Exception:
            pass
        driver.save_screenshot(str(EVIDENCE_DIR / "demo_razorpay_checkout_modal.png"))

        # 7. Dashboard & Orders History
        driver.get(f"{BASE_URL}/orders")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='orders-table']")))
        time.sleep(1.0)
        driver.get(f"{BASE_URL}/dashboard")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='user-dashboard']")))
        time.sleep(1.0)

        # 8. Show generated Pytest HTML test reports in the demo video
        api_report = (PROJECT_ROOT / "reports" / "api_report.html").resolve().as_uri()
        e2e_report = (PROJECT_ROOT / "reports" / "e2e_report.html").resolve().as_uri()
        driver.get(api_report)
        time.sleep(1.5)
        driver.get(e2e_report)
        time.sleep(1.5)
    finally:
        saved = recorder.stop()
        driver.quit()
        print(f"DEMO_VIDEO={saved}")


if __name__ == "__main__":
    run_demo()
