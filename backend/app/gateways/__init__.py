"""Payment gateway abstractions and provider factory."""

from .base import GatewayInitiationResult, GatewayVerificationResult, PaymentGateway
from .razorpay_gateway import RazorpayGateway
from .stripe_gateway import StripeGateway

__all__ = [
    "GatewayInitiationResult",
    "GatewayVerificationResult",
    "PaymentGateway",
    "RazorpayGateway",
    "StripeGateway",
    "get_gateway",
]


def get_gateway(provider: str) -> PaymentGateway:
    """Return concrete PaymentGateway instance for the requested provider."""
    normalized = provider.strip().lower()
    if normalized == "stripe":
        return StripeGateway()
    if normalized == "razorpay":
        return RazorpayGateway()
    raise ValueError(f"Unsupported payment provider: {provider}")
