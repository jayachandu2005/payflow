"""Product catalog and product detail Page Objects."""

from selenium.webdriver.common.by import By

from automation.pages.base_page import BasePage


class ProductsPage(BasePage):
    SEARCH_INPUT = (By.CSS_SELECTOR, "[data-testid='products-search']")
    CATEGORY_SELECT = (By.CSS_SELECTOR, "[data-testid='products-category']")
    NAV_CART = (By.CSS_SELECTOR, "[data-testid='nav-cart']")
    FIRST_PRODUCT_LINK = (By.CSS_SELECTOR, "[data-testid^='product-details-']")

    def open_catalog(self) -> None:
        self.open("/products")
        self.wait_visible(self.FIRST_PRODUCT_LINK)

    def search_product(self, query: str) -> None:
        self.type_text(self.SEARCH_INPUT, query)

    def open_first_product(self) -> None:
        elem = self.wait_clickable(self.FIRST_PRODUCT_LINK)
        self.driver.execute_script("arguments[0].click();", elem)
        self.wait_url_contains("/products/")

    def add_product_by_id(self, product_id: int) -> None:
        self.click((By.CSS_SELECTOR, f"[data-testid='add-to-cart-{product_id}']"))


class ProductDetailPage(BasePage):
    TITLE = (By.CSS_SELECTOR, "[data-testid='product-detail-title']")
    PRICE = (By.CSS_SELECTOR, "[data-testid='product-detail-price']")
    QUANTITY = (By.CSS_SELECTOR, "[data-testid='detail-quantity']")
    ADD_TO_CART_BTN = (By.CSS_SELECTOR, "[data-testid='detail-add-to-cart']")
    ADDED_ALERT = (By.CSS_SELECTOR, "[data-testid='detail-added-alert']")
    NAV_CART = (By.CSS_SELECTOR, "[data-testid='nav-cart']")

    def get_title(self) -> str:
        return self.wait_visible(self.TITLE).text

    def add_to_cart(self, quantity: int = 1) -> None:
        self.type_text(self.QUANTITY, str(quantity))
        self.click(self.ADD_TO_CART_BTN)
        self.wait_visible(self.ADDED_ALERT)

    def go_to_cart(self) -> None:
        self.click(self.NAV_CART)
        self.wait_url_contains("/cart")
