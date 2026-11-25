"""Official Razorpay Test Mode integration using the razorpay Python SDK."""

from typing import Any, Dict, Optional

import razorpay
from razorpay.errors import BadRequestError, SignatureVerificationError

from ..config import get_settings
from ..models import Order, Payment
from ..security import sanitize_payload
from .base import GatewayInitiationResult, GatewayVerificationResult, PaymentGateway


class RazorpayGateway(PaymentGateway):
    """Razorpay sandbox implementation supporting Orders + Checkout + 3DS OTP."""

    provider_name = "razorpay"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self) -> razorpay.Client:
        if not self.is_configured():
            raise RuntimeError(
                "Razorpay test credentials are not configured. Set valid RAZORPAY_KEY_ID (rzp_test_...) "
                "and RAZORPAY_KEY_SECRET in .env."
            )
        return razorpay.Client(auth=(self.settings.RAZORPAY_KEY_ID, self.settings.RAZORPAY_KEY_SECRET))

    def is_configured(self) -> bool:
        return self.settings.razorpay_configured

    def _to_inr_paise(self, amount_cents: int, currency: str) -> int:
        if currency.upper() == "INR":
            return amount_cents
        # Convert USD cents to INR paise cleanly for Razorpay Indian sandbox accounts
        usd_amount = amount_cents / 100.0
        return max(100, round(usd_amount * self.settings.USD_TO_INR_RATE * 100))

    def initiate_payment(
        self,
        order: Order,
        payment_id: int,
        payment_method: str,
        idempotency_key: str,
    ) -> GatewayInitiationResult:
        client = self._client()
        charge_paise = self._to_inr_paise(order.total_cents, order.currency)

        rzp_order = client.order.create(
            {
                "amount": charge_paise,
                "currency": "INR",
                "receipt": f"{order.order_number}-{payment_id}",
                "payment_capture": 1,
                "notes": {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "payment_id": str(payment_id),
                    "idempotency_key": idempotency_key,
                },
            }
        )

        summary = sanitize_payload(
            {
                "id": rzp_order.get("id"),
                "status": rzp_order.get("status"),
                "amount": rzp_order.get("amount"),
                "currency": rzp_order.get("currency"),
            }
        )

        return GatewayInitiationResult(
            gateway_order_id=rzp_order["id"],
            gateway_payment_id=None,
            amount_cents=charge_paise,
            currency="INR",
            status="created",
            checkout_url=None,
            frontend_payload={
                "mode": "razorpay_checkout",
                "key_id": self.settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": rzp_order["id"],
                "amount": rzp_order["amount"],
                "currency": rzp_order["currency"],
                "name": "PayFlow Store",
                "description": f"Order {order.order_number}",
                "prefill": {
                    "name": order.customer_name,
                    "email": order.customer_email,
                    "contact": order.customer_phone,
                },
                "notes": {
                    "order_number": order.order_number,
                    "payment_id": str(payment_id),
                },
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
        rzp_order_id = gateway_order_id or payment.gateway_order_id
        rzp_payment_id = gateway_payment_id or payment.gateway_payment_id

        # Step 1: Verify callback HMAC signature if signature was provided by frontend
        if gateway_signature:
            if not rzp_order_id or not rzp_payment_id:
                return GatewayVerificationResult(
                    status="failed",
                    gateway_status="invalid_signature_params",
                    gateway_payment_id=rzp_payment_id,
                    failure_reason="Missing Razorpay order_id or payment_id for signature verification",
                    message="Payment verification failed: missing parameters.",
                    sanitized_summary={},
                )
            try:
                client.utility.verify_payment_signature(
                    {
                        "razorpay_order_id": rzp_order_id,
                        "razorpay_payment_id": rzp_payment_id,
                        "razorpay_signature": gateway_signature,
                    }
                )
            except SignatureVerificationError as exc:
                return GatewayVerificationResult(
                    status="failed",
                    gateway_status="signature_mismatch",
                    gateway_payment_id=rzp_payment_id,
                    failure_reason="Razorpay payment signature verification failed",
                    message="Payment signature verification failed.",
                    sanitized_summary={"error": str(exc)},
                )

        # Step 2: Query Razorpay authoritative Payment / Order API
        rzp_payment: Optional[Dict[str, Any]] = None
        if rzp_payment_id:
            rzp_payment = client.payment.fetch(rzp_payment_id)
        elif rzp_order_id:
            order_payments = client.order.payments(rzp_order_id)
            items = order_payments.get("items", []) if isinstance(order_payments, dict) else []
            if items:
                # Prefer captured/authorized payment, otherwise inspect latest attempt
                captured = [p for p in items if p.get("status") == "captured"]
                rzp_payment = captured[0] if captured else items[-1]

        if not rzp_payment:
            # Check order status directly
            if rzp_order_id:
                rzp_order = client.order.fetch(rzp_order_id)
                return GatewayVerificationResult(
                    status="pending",
                    gateway_status=rzp_order.get("status", "created"),
                    gateway_payment_id=None,
                    failure_reason=None,
                    message="No payment attempt recorded on Razorpay order yet.",
                    sanitized_summary=sanitize_payload(rzp_order),
                )
            return GatewayVerificationResult(
                status="failed",
                gateway_status="not_found",
                gateway_payment_id=None,
                failure_reason="No Razorpay payment or order reference found",
                message="Payment could not be verified.",
                sanitized_summary={},
            )

        result = self._map_rzp_payment(client, rzp_payment)
        if result.status == "succeeded" and (
            int(rzp_payment.get("amount", 0)) < payment.amount_cents
            or str(rzp_payment.get("currency", "")).upper() != payment.currency.upper()
        ):
            return GatewayVerificationResult(
                status="failed",
                gateway_status="amount_mismatch",
                gateway_payment_id=result.gateway_payment_id,
                failure_reason="Razorpay payment amount or currency does not match expected order total",
                message="Payment verification failed due to amount/currency mismatch.",
                sanitized_summary=result.sanitized_summary,
            )
        return result

    def _map_rzp_payment(self, client: razorpay.Client, rzp_payment: Dict[str, Any]) -> GatewayVerificationResult:
        raw_status = rzp_payment.get("status", "created")
        pay_id = rzp_payment.get("id")
        amount = rzp_payment.get("amount")
        err_desc = rzp_payment.get("error_description") or rzp_payment.get("error_reason")

        # If authorized but not captured yet, capture authoritatively
        if raw_status == "authorized" and pay_id and amount:
            try:
                rzp_payment = client.payment.capture(pay_id, amount, {"currency": rzp_payment.get("currency", "INR")})
                raw_status = rzp_payment.get("status", raw_status)
            except BadRequestError:
                pass

        if raw_status == "captured":
            status = "succeeded"
            message = "Payment verified and captured by Razorpay."
            failure_reason = None
        elif raw_status in ("created", "authorized"):
            status = "pending"
            message = f"Payment status is {raw_status} at Razorpay."
            failure_reason = None
        elif raw_status == "failed":
            status = "failed"
            failure_reason = err_desc or "Payment failed during 3DS/OTP authentication or bank decline"
            message = f"Payment failed: {failure_reason}"
        else:
            status = "pending"
            failure_reason = err_desc
            message = f"Razorpay payment status: {raw_status}"

        return GatewayVerificationResult(
            status=status,
            gateway_status=raw_status,
            gateway_payment_id=pay_id,
            failure_reason=failure_reason,
            message=message,
            sanitized_summary=sanitize_payload(
                {
                    "id": pay_id,
                    "order_id": rzp_payment.get("order_id"),
                    "status": raw_status,
                    "method": rzp_payment.get("method"),
                    "amount": amount,
                    "currency": rzp_payment.get("currency"),
                    "error_code": rzp_payment.get("error_code"),
                    "error_description": err_desc,
                }
            ),
        )

    def cancel_payment(self, payment: Payment) -> GatewayVerificationResult:
        return GatewayVerificationResult(
            status="cancelled",
            gateway_status="cancelled_by_user",
            gateway_payment_id=payment.gateway_payment_id,
            failure_reason="Customer dismissed or cancelled Razorpay Checkout",
            message="Payment was cancelled before completion.",
            sanitized_summary={"razorpay_order_id": payment.gateway_order_id},
        )

    def verify_webhook_signature(self, body_str: str, sig_header: str) -> None:
        """Verify Razorpay webhook HMAC signature using RAZORPAY_WEBHOOK_SECRET."""
        if not self.settings.razorpay_webhook_configured:
            raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is not configured")
        utility = razorpay.Utility(None)
        utility.verify_webhook_signature(body_str, sig_header, self.settings.RAZORPAY_WEBHOOK_SECRET)
