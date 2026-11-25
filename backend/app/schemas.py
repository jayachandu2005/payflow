"""Pydantic v2 request and response schemas with strict validation."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ------------------------------------------------------------------------------
# Auth & User
# ------------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ------------------------------------------------------------------------------
# Products
# ------------------------------------------------------------------------------
class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=220, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=10, max_length=4000)
    price_cents: int = Field(ge=100, le=100_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=10)
    image_url: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=2, max_length=100)
    stock: int = Field(default=50, ge=0, le=100_000)


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    price_cents: Optional[int] = Field(default=None, ge=100, le=100_000_000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    stock: Optional[int] = Field(default=None, ge=0, le=100_000)
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    price_cents: int
    currency: str
    image_url: str
    category: str
    stock: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Cart
# ------------------------------------------------------------------------------
class CartAddRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=50)


class CartUpdateRequest(BaseModel):
    quantity: int = Field(ge=0, le=50)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut
    line_total_cents: int


class CartOut(BaseModel):
    items: List[CartItemOut]
    item_count: int
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str = "USD"


# ------------------------------------------------------------------------------
# Orders & Checkout
# ------------------------------------------------------------------------------
class CheckoutCustomerInfo(BaseModel):
    customer_name: str = Field(min_length=2, max_length=150)
    customer_email: EmailStr
    customer_phone: str = Field(min_length=7, max_length=30)
    shipping_address: str = Field(min_length=5, max_length=300)
    shipping_city: str = Field(min_length=2, max_length=120)
    shipping_postal_code: str = Field(min_length=3, max_length=30)
    shipping_country: str = Field(min_length=2, max_length=80)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = [c for c in value if c.isdigit()]
        if len(digits) < 7:
            raise ValueError("Phone number must contain at least 7 digits")
        return value.strip()


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int

    model_config = {"from_attributes": True}


class PaymentSummaryOut(BaseModel):
    id: int
    order_id: int
    provider: str
    payment_method: str
    gateway_order_id: Optional[str]
    gateway_payment_id: Optional[str]
    idempotency_key: str
    amount_cents: int
    currency: str
    status: str
    failure_reason: Optional[str]
    checkout_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: int
    payment_id: int
    order_id: int
    transaction_type: str
    status: str
    gateway_reference: Optional[str]
    amount_cents: int
    currency: str
    raw_summary_json: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_number: str
    user_id: int
    status: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: str
    shipping_city: str
    shipping_postal_code: str
    shipping_country: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut] = []
    payments: List[PaymentSummaryOut] = []

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Payments
# ------------------------------------------------------------------------------
class GatewayMethodInfo(BaseModel):
    provider: Literal["stripe", "razorpay"]
    payment_method: str
    label: str
    description: str
    configured: bool
    supports_3ds_otp: bool
    currency: str


class PaymentConfigOut(BaseModel):
    stripe_configured: bool
    stripe_publishable_key: Optional[str] = None
    razorpay_configured: bool
    razorpay_key_id: Optional[str] = None
    usd_to_inr_rate: float
    available_methods: List[GatewayMethodInfo]


class PaymentInitiateRequest(BaseModel):
    order_id: int = Field(gt=0)
    provider: Literal["stripe", "razorpay"]
    payment_method: Literal["card", "stripe_checkout", "razorpay_checkout"] = "card"
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=128)


class PaymentInitiateResponse(BaseModel):
    payment: PaymentSummaryOut
    order_status: str
    gateway_payload: Dict[str, Any]


class PaymentVerifyRequest(BaseModel):
    payment_id: int = Field(gt=0)
    gateway_payment_id: Optional[str] = None
    gateway_order_id: Optional[str] = None
    gateway_signature: Optional[str] = None


class PaymentCancelRequest(BaseModel):
    payment_id: int = Field(gt=0)
    reason: Optional[str] = Field(default="Cancelled by user at checkout", max_length=300)


class PaymentVerifyResponse(BaseModel):
    payment: PaymentSummaryOut
    order: OrderOut
    verified_authoritatively: bool
    gateway_status: str
    message: str


class WebhookEventOut(BaseModel):
    id: int
    provider: str
    event_id: str
    event_type: str
    signature_valid: bool
    processed: bool
    processing_error: Optional[str]
    received_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}
