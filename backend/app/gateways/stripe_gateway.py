"""Official Stripe Sandbox integration using the stripe Python SDK."""

from typing import Any, Dict, Optional

import stripe

from ..config import get_settings
from ..models import Order, Payment
from ..security import sanitize_payload
from .base import GatewayInitiationResult, GatewayVerificationResult, PaymentGateway


class StripeGateway(PaymentGateway):
    """Stripe sandbox implementation supporting PaymentIntents (3DS2) and Checkout Sessions."""

    provider_name = "stripe"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self) -> stripe.StripeClient:
        if not self.is_configured():
            raise RuntimeError(
                "Stripe sandbox credentials are not configured. Set valid STRIPE_SECRET_KEY (sk_test_...) "
                "and STRIPE_PUBLISHABLE_KEY (pk_test_...) in .env."
            )
        return stripe.StripeClient(api_key=self.settings.STRIPE_SECRET_KEY)

    def is_configured(self) -> bool:
        return self.settings.stripe_configured

    def initiate_payment(
        self,
        order: Order,
        payment_id: int,
        payment_method: str,
        idempotency_key: str,
    ) -> GatewayInitiationResult:
        client = self._client()
        currency = order.currency.lower()

        if payment_method == "stripe_checkout":
            line_items = [
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": item.product_name},
                        "unit_amount": item.unit_price_cents,
                    },
                    "quantity": item.quantity,
                }
                for item in order.items
            ]
            if order.tax_cents > 0:
                line_items.append(
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": "Estimated Tax"},
                            "unit_amount": order.tax_cents,
                        },
                        "quantity": 1,
                    }
                )

            session = client.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "payment_method_types": ["card"],
                    "customer_email": order.customer_email,
                    "line_items": line_items,
                    "success_url": (
                        f"{self.settings.FRONTEND_URL}/payment/result/{order.id}"
                        f"?payment_id={payment_id}&session_id={{CHECKOUT_SESSION_ID}}"
                    ),
                    "cancel_url": (
                        f"{self.settings.FRONTEND_URL}/payment/result/{order.id}"
                        f"?payment_id={payment_id}&cancelled=1"
                    ),
                    "metadata": {
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "payment_id": str(payment_id),
                    },
                    "payment_intent_data": {
                        "metadata": {
                            "order_id": str(order.id),
                            "order_number": order.order_number,
                            "payment_id": str(payment_id),
                        }
                    },
                },
                options={"idempotency_key": f"cs-{idempotency_key}"},
            )
            summary = sanitize_payload(
                {
                    "id": session.id,
                    "status": session.status,
                    "payment_status": session.payment_status,
                    "amount_total": session.amount_total,
                    "currency": session.currency,
                }
            )
            return GatewayInitiationResult(
                gateway_order_id=session.id,
                gateway_payment_id=str(session.payment_intent) if session.payment_intent else None,
                amount_cents=order.total_cents,
                currency=order.currency.upper(),
                status="created",
                checkout_url=session.url,
                frontend_payload={
                    "mode": "stripe_checkout",
                    "session_id": session.id,
                    "checkout_url": session.url,
                    "publishable_key": self.settings.STRIPE_PUBLISHABLE_KEY,
                },
                sanitized_summary=summary,
            )

        # Default: PaymentIntent for Stripe Elements + 3D Secure 2 modal
        pi = client.payment_intents.create(
            params={
                "amount": order.total_cents,
                "currency": currency,
                "payment_method_types": ["card"],
                "receipt_email": order.customer_email,
                "description": f"PayFlow Order {order.order_number}",
                "metadata": {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "payment_id": str(payment_id),
                },
            },
            options={"idempotency_key": f"pi-{idempotency_key}"},
        )
        summary = sanitize_payload(
            {
                "id": pi.id,
                "status": pi.status,
                "amount": pi.amount,
                "currency": pi.currency,
            }
        )
        return GatewayInitiationResult(
            gateway_order_id=pi.id,
            gateway_payment_id=pi.id,
            amount_cents=order.total_cents,
            currency=order.currency.upper(),
            status="created",
            checkout_url=None,
            frontend_payload={
                "mode": "stripe_elements",
                "payment_intent_id": pi.id,
                "client_secret": pi.client_secret,
                "publishable_key": self.settings.STRIPE_PUBLISHABLE_KEY,
                "amount_cents": order.total_cents,
                "currency": order.currency.upper(),
            },
            sanitized_summary=summary,
        )

    def verify_payment(
        self,
        payment: Payment,
        gateway_payment_id: Optional[str] = None,
        gateway_order_id: Optional[str] = None,
        gateway_signature: Optional[str] = None,
    ) -> GatewayVerificationResult:
        client = self._client()
        target_id = gateway_order_id or payment.gateway_order_id
        if not target_id:
            return GatewayVerificationResult(
                status="failed",
                gateway_status="missing_reference",
                gateway_payment_id=None,
                failure_reason="Missing Stripe PaymentIntent or Checkout Session ID",
                message="Payment verification failed: missing gateway reference.",
                sanitized_summary={},
            )

        if target_id.startswith("cs_"):
            session = client.checkout.sessions.retrieve(
                target_id,
                params={"expand": ["payment_intent"]},
            )
            pi_obj = session.payment_intent
            if pi_obj and not isinstance(pi_obj, str):
                return self._map_payment_intent(pi_obj)

            if session.status == "expired":
                return GatewayVerificationResult(
                    status="cancelled",
                    gateway_status="expired",
                    gateway_payment_id=None,
                    failure_reason="Stripe Checkout session expired or was cancelled",
                    message="Payment session was cancelled or expired.",
                    sanitized_summary=sanitize_payload(
                        {"session_id": session.id, "status": session.status, "payment_status": session.payment_status}
                    ),
                )
            mapped_status = "succeeded" if session.payment_status == "paid" else "pending"
            return GatewayVerificationResult(
                status=mapped_status,
                gateway_status=f"{session.status}:{session.payment_status}",
                gateway_payment_id=str(pi_obj) if pi_obj else None,
                failure_reason=None,
                message="Stripe Checkout session status verified.",
                sanitized_summary=sanitize_payload(
                    {"session_id": session.id, "status": session.status, "payment_status": session.payment_status}
                ),
            )

        pi = client.payment_intents.retrieve(target_id)
        result = self._map_payment_intent(pi)
        # Guard against partial/mismatched amounts ever marking an order succeeded
        if result.status == "succeeded" and (
            pi.amount < payment.amount_cents or str(pi.currency).upper() != payment.currency.upper()
        ):
            return GatewayVerificationResult(
                status="failed",
                gateway_status="amount_mismatch",
                gateway_payment_id=pi.id,
                failure_reason="Stripe payment amount or currency does not match expected order total",
                message="Payment verification failed due to amount/currency mismatch.",
                sanitized_summary=result.sanitized_summary,
            )
        return result

    def _map_payment_intent(self, pi: Any) -> GatewayVerificationResult:
        raw_status = pi.status
        last_error = getattr(pi, "last_payment_error", None)
        error_msg = getattr(last_error, "message", None) if last_error else None
        error_code = getattr(last_error, "code", None) if last_error else None

        if raw_status == "succeeded":
            status = "succeeded"
            message = "Payment verified and succeeded via Stripe API."
            failure_reason = None
        elif raw_status == "processing":
            status = "pending"
            message = "Payment is currently processing with Stripe."
            failure_reason = None
        elif raw_status in ("requires_action", "requires_confirmation"):
            status = "requires_action"
            message = "3D Secure authentication is required to complete payment."
            failure_reason = error_msg
        elif raw_status == "canceled":
            status = "cancelled"
            message = "Payment was cancelled."
            failure_reason = getattr(pi, "cancellation_reason", None) or "Cancelled"
        elif raw_status == "requires_payment_method":
            if last_error:
                status = "failed"
                failure_reason = f"{error_code}: {error_msg}" if error_code else (error_msg or "Card declined")
                message = f"Payment failed: {failure_reason}"
            else:
                status = "pending"
                failure_reason = None
                message = "Payment has not been submitted yet."
        else:
            status = "pending"
            failure_reason = error_msg
            message = f"Stripe PaymentIntent status: {raw_status}"

        return GatewayVerificationResult(
            status=status,
            gateway_status=raw_status,
            gateway_payment_id=pi.id,
            failure_reason=failure_reason,
            message=message,
            sanitized_summary=sanitize_payload(
                {
                    "id": pi.id,
                    "status": raw_status,
                    "amount": pi.amount,
                    "currency": pi.currency,
                    "last_payment_error_code": error_code,
                    "last_payment_error_message": error_msg,
                }
            ),
        )

    def cancel_payment(self, payment: Payment) -> GatewayVerificationResult:
        client = self._client()
        target_id = payment.gateway_order_id
        if not target_id:
            return GatewayVerificationResult(
                status="cancelled",
                gateway_status="local_cancelled",
                gateway_payment_id=None,
                failure_reason="Cancelled before gateway initiation",
                message="Payment cancelled.",
                sanitized_summary={},
            )

        if target_id.startswith("cs_"):
            session = client.checkout.sessions.retrieve(target_id)
            if session.status == "open":
                session = client.checkout.sessions.expire(target_id)
            return GatewayVerificationResult(
                status="cancelled",
                gateway_status=session.status,
                gateway_payment_id=str(session.payment_intent) if session.payment_intent else None,
                failure_reason="Cancelled by customer",
                message="Stripe Checkout session expired.",
                sanitized_summary={"session_id": session.id, "status": session.status},
            )

        pi = client.payment_intents.retrieve(target_id)
        if pi.status not in ("succeeded", "canceled"):
            pi = client.payment_intents.cancel(target_id, params={"cancellation_reason": "abandoned"})
        return self._map_payment_intent(pi)

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Verify Stripe webhook signature using STRIPE_WEBHOOK_SECRET."""
        if not self.settings.stripe_webhook_configured:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=self.settings.STRIPE_WEBHOOK_SECRET,
        )
        return dict(event)
