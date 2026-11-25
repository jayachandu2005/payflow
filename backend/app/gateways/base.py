"""Base payment gateway interface and standardized result dataclasses."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..models import Order, Payment


@dataclass
class GatewayInitiationResult:
    gateway_order_id: str
    gateway_payment_id: Optional[str]
    amount_cents: int
    currency: str
    status: str
    checkout_url: Optional[str]
    frontend_payload: Dict[str, Any]
    sanitized_summary: Dict[str, Any]


@dataclass
class GatewayVerificationResult:
    status: str  # succeeded | pending | requires_action | failed | cancelled
    gateway_status: str
    gateway_payment_id: Optional[str]
    failure_reason: Optional[str]
    message: str
    sanitized_summary: Dict[str, Any]


class PaymentGateway(ABC):
    """Abstract interface implemented by official sandbox payment providers."""

    provider_name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if genuine sandbox credentials are configured."""

    @abstractmethod
    def initiate_payment(
        self,
        order: Order,
        payment_id: int,
        payment_method: str,
        idempotency_key: str,
    ) -> GatewayInitiationResult:
        """Create a genuine payment request/intent/order with the gateway SDK."""

    @abstractmethod
    def verify_payment(
        self,
        payment: Payment,
        gateway_payment_id: Optional[str] = None,
        gateway_order_id: Optional[str] = None,
        gateway_signature: Optional[str] = None,
    ) -> GatewayVerificationResult:
        """Query the gateway's authoritative API to determine real transaction status."""

    @abstractmethod
    def cancel_payment(self, payment: Payment) -> GatewayVerificationResult:
        """Cancel an open payment intent/order if supported by the gateway."""
