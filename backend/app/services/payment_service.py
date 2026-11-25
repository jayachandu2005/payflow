"""Payment orchestration, authoritative verification, and order synchronization service."""

import json
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..gateways import get_gateway
from ..gateways.base import GatewayVerificationResult
from ..models import Order, Payment, Product, Transaction
from ..security import sanitize_payload


def _record_transaction(
    db: Session,
    payment: Payment,
    transaction_type: str,
    tx_status: str,
    gateway_reference: Optional[str],
    summary: Dict[str, Any],
) -> Transaction:
    """Persist an immutable sanitized transaction ledger row."""
    tx = Transaction(
        payment_id=payment.id,
        order_id=payment.order_id,
        transaction_type=transaction_type,
        status=tx_status,
        gateway_reference=gateway_reference,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        raw_summary_json=json.dumps(sanitize_payload(summary)),
    )
    db.add(tx)
    return tx


def _sync_order_status_from_payment(db: Session, order: Order, payment_status: str) -> None:
    """Keep Order.status strictly synchronized with authoritative Payment.status."""
    if payment_status == "succeeded":
        if order.status != "paid":
            # Decrement product stock atomically when transitioning to paid
            for item in order.items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                if product:
                    product.stock = max(0, product.stock - item.quantity)
            order.status = "paid"
    elif payment_status in ("created", "pending", "requires_action"):
        if order.status not in ("paid",):
            order.status = "payment_initiated"
    elif payment_status == "failed":
        if order.status not in ("paid",):
            order.status = "failed"
    elif payment_status == "cancelled":
        if order.status not in ("paid",):
            order.status = "cancelled"


def initiate_payment_for_order(
    db: Session,
    order: Order,
    user_id: int,
    provider: str,
    payment_method: str,
    idempotency_key: Optional[str],
) -> Tuple[Payment, Dict[str, Any]]:
    """Create or return an idempotent gateway payment request for an order."""
    if order.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has already been paid.",
        )

    idem_key = idempotency_key or f"order-{order.id}-{provider}-{payment_method}-{uuid.uuid4().hex[:12]}"

    # Idempotency guard: return existing payment if same key already exists
    existing = db.query(Payment).filter(Payment.idempotency_key == idem_key).first()
    if existing:
        if existing.order_id != order.id or existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key conflict for another order.",
            )
        cached_payload = json.loads(existing.metadata_json) if existing.metadata_json else {}
        return existing, cached_payload

    gateway = get_gateway(provider)
    if not gateway.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"{provider.capitalize()} sandbox credentials are not configured in .env. "
                "Please set official sandbox test keys before initiating payment."
            ),
        )

    # Create pending payment row first to acquire a database ID
    payment = Payment(
        order_id=order.id,
        user_id=user_id,
        provider=provider,
        payment_method=payment_method,
        idempotency_key=idem_key,
        amount_cents=order.total_cents,
        currency=order.currency,
        status="created",
    )
    db.add(payment)
    db.flush()

    try:
        result = gateway.initiate_payment(
            order=order,
            payment_id=payment.id,
            payment_method=payment_method,
            idempotency_key=idem_key,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gateway initiation failed ({provider}): {exc}",
        ) from exc

    payment.gateway_order_id = result.gateway_order_id
    payment.gateway_payment_id = result.gateway_payment_id
    payment.amount_cents = result.amount_cents
    payment.currency = result.currency
    payment.status = result.status
    payment.checkout_url = result.checkout_url
    payment.metadata_json = json.dumps(sanitize_payload(result.frontend_payload))

    order.status = "payment_initiated"

    _record_transaction(
        db=db,
        payment=payment,
        transaction_type="initiation",
        tx_status=result.status,
        gateway_reference=result.gateway_order_id,
        summary=result.sanitized_summary,
    )

    db.commit()
    db.refresh(payment)
    return payment, result.frontend_payload


def verify_payment_authoritatively(
    db: Session,
    payment: Payment,
    gateway_payment_id: Optional[str] = None,
    gateway_order_id: Optional[str] = None,
    gateway_signature: Optional[str] = None,
    source: str = "verification",
) -> Tuple[Payment, Order, GatewayVerificationResult]:
    """Query the gateway's authoritative API and synchronize Payment + Order state."""
    # Prevent cross-order verification spoofing by rejecting mismatched gateway order IDs
    if gateway_order_id and payment.gateway_order_id and gateway_order_id != payment.gateway_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gateway order reference mismatch for this payment.",
        )

    gateway = get_gateway(payment.provider)
    if not gateway.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{payment.provider.capitalize()} sandbox credentials are not configured.",
        )

    try:
        verification = gateway.verify_payment(
            payment=payment,
            gateway_payment_id=gateway_payment_id,
            gateway_order_id=payment.gateway_order_id or gateway_order_id,
            gateway_signature=gateway_signature,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment with {payment.provider}: {exc}",
        ) from exc

    if verification.gateway_payment_id:
        payment.gateway_payment_id = verification.gateway_payment_id

    # Never downgrade an already succeeded payment back to pending/failed
    if payment.status != "succeeded":
        payment.status = verification.status
        payment.failure_reason = verification.failure_reason

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _sync_order_status_from_payment(db, order, payment.status)
    _record_transaction(
        db=db,
        payment=payment,
        transaction_type=source,
        tx_status=verification.status,
        gateway_reference=verification.gateway_payment_id or payment.gateway_order_id,
        summary=verification.sanitized_summary,
    )

    db.commit()
    db.refresh(payment)
    db.refresh(order)
    return payment, order, verification


def cancel_payment_for_order(
    db: Session,
    payment: Payment,
    reason: Optional[str] = None,
) -> Tuple[Payment, Order, GatewayVerificationResult]:
    """Cancel an unpaid payment safely without overwriting paid orders."""
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if payment.status == "succeeded" or order.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a payment that has already succeeded.",
        )

    gateway = get_gateway(payment.provider)
    if gateway.is_configured():
        result = gateway.cancel_payment(payment)
    else:
        result = GatewayVerificationResult(
            status="cancelled",
            gateway_status="cancelled",
            gateway_payment_id=payment.gateway_payment_id,
            failure_reason=reason or "Cancelled by user",
            message="Payment cancelled.",
            sanitized_summary={},
        )

    payment.status = result.status
    payment.failure_reason = reason or result.failure_reason
    _sync_order_status_from_payment(db, order, payment.status)
    _record_transaction(
        db=db,
        payment=payment,
        transaction_type="cancellation",
        tx_status=result.status,
        gateway_reference=payment.gateway_order_id,
        summary=result.sanitized_summary,
    )
    db.commit()
    db.refresh(payment)
    db.refresh(order)
    return payment, order, result
