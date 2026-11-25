"""Cryptographically verified webhook handlers with idempotent event deduplication."""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..gateways.razorpay_gateway import RazorpayGateway
from ..gateways.stripe_gateway import StripeGateway
from ..models import Order, Payment, Transaction, WebhookEvent
from ..security import sanitize_payload
from ..services.payment_service import _sync_order_status_from_payment

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


def _apply_webhook_status(
    db: Session,
    payment: Payment,
    new_status: str,
    gateway_payment_id: str | None,
    failure_reason: str | None,
    gateway_ref: str | None,
    summary: dict,
) -> None:
    if gateway_payment_id:
        payment.gateway_payment_id = gateway_payment_id
    if payment.status != "succeeded":
        payment.status = new_status
        payment.failure_reason = failure_reason

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        _sync_order_status_from_payment(db, order, payment.status)

    db.add(
        Transaction(
            payment_id=payment.id,
            order_id=payment.order_id,
            transaction_type="webhook",
            status=new_status,
            gateway_reference=gateway_ref,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            raw_summary_json=json.dumps(sanitize_payload(summary)),
        )
    )


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle and verify official Stripe webhook events idempotently."""
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    gateway = StripeGateway()

    try:
        event = gateway.construct_webhook_event(raw_body, sig_header)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        # Record failed signature attempt for auditability
        fallback_id = f"invalid-{hashlib.sha256(raw_body).hexdigest()[:24]}"
        if not db.query(WebhookEvent).filter(
            WebhookEvent.provider == "stripe", WebhookEvent.event_id == fallback_id
        ).first():
            db.add(
                WebhookEvent(
                    provider="stripe",
                    event_id=fallback_id,
                    event_type="invalid_signature",
                    signature_valid=False,
                    payload_json=raw_body.decode("utf-8", errors="replace")[:4000],
                    processed=False,
                    processing_error=str(exc),
                )
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Stripe webhook signature: {exc}",
        ) from exc

    event_id = str(event.get("id", ""))
    event_type = str(event.get("type", "unknown"))

    # Deduplicate already-processed webhook events
    existing = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.provider == "stripe", WebhookEvent.event_id == event_id)
        .first()
    )
    if existing:
        return {"received": True, "duplicate": True, "event_id": event_id}

    webhook_row = WebhookEvent(
        provider="stripe",
        event_id=event_id,
        event_type=event_type,
        signature_valid=True,
        payload_json=json.dumps(sanitize_payload(event)),
        processed=False,
    )
    db.add(webhook_row)
    db.flush()

    data_obj = event.get("data", {}).get("object", {})
    obj_id = data_obj.get("id")
    payment = None
    if obj_id:
        payment = (
            db.query(Payment)
            .filter(
                Payment.provider == "stripe",
                (Payment.gateway_order_id == obj_id) | (Payment.gateway_payment_id == obj_id),
            )
            .first()
        )
    if not payment and isinstance(data_obj.get("metadata"), dict) and data_obj["metadata"].get("payment_id"):
        try:
            pid = int(data_obj["metadata"]["payment_id"])
            payment = db.query(Payment).filter(Payment.id == pid).first()
        except (TypeError, ValueError):
            payment = None

    if payment:
        if event_type in ("payment_intent.succeeded", "checkout.session.completed"):
            pi_ref = data_obj.get("payment_intent") or obj_id
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="succeeded",
                gateway_payment_id=str(pi_ref) if pi_ref else None,
                failure_reason=None,
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type, "object_id": obj_id},
            )
        elif event_type == "payment_intent.payment_failed":
            last_err = data_obj.get("last_payment_error") or {}
            reason = last_err.get("message") or "Payment failed"
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="failed",
                gateway_payment_id=obj_id,
                failure_reason=reason,
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type, "reason": reason},
            )
        elif event_type in ("payment_intent.canceled", "checkout.session.expired"):
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="cancelled",
                gateway_payment_id=obj_id,
                failure_reason="Cancelled or expired at Stripe",
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type},
            )
        elif event_type == "payment_intent.processing":
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="pending",
                gateway_payment_id=obj_id,
                failure_reason=None,
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type},
            )

    webhook_row.processed = True
    webhook_row.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"received": True, "duplicate": False, "event_id": event_id, "event_type": event_type}


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle and verify official Razorpay webhook events idempotently."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="replace")
    sig_header = request.headers.get("x-razorpay-signature", "")
    gateway = RazorpayGateway()

    try:
        gateway.verify_webhook_signature(body_str, sig_header)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        fallback_id = f"invalid-{hashlib.sha256(raw_body).hexdigest()[:24]}"
        if not db.query(WebhookEvent).filter(
            WebhookEvent.provider == "razorpay", WebhookEvent.event_id == fallback_id
        ).first():
            db.add(
                WebhookEvent(
                    provider="razorpay",
                    event_id=fallback_id,
                    event_type="invalid_signature",
                    signature_valid=False,
                    payload_json=body_str[:4000],
                    processed=False,
                    processing_error=str(exc),
                )
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Razorpay webhook signature: {exc}",
        ) from exc

    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON webhook payload: {exc}",
        ) from exc
    event_type = str(payload.get("event", "unknown"))
    event_id = (
        request.headers.get("x-razorpay-event-id")
        or hashlib.sha256(raw_body).hexdigest()[:32]
    )

    existing = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.provider == "razorpay", WebhookEvent.event_id == event_id)
        .first()
    )
    if existing:
        return {"received": True, "duplicate": True, "event_id": event_id}

    webhook_row = WebhookEvent(
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        signature_valid=True,
        payload_json=json.dumps(sanitize_payload(payload)),
        processed=False,
    )
    db.add(webhook_row)
    db.flush()

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
    rzp_order_id = payment_entity.get("order_id") or order_entity.get("id")
    rzp_payment_id = payment_entity.get("id")

    payment = None
    if rzp_order_id:
        payment = (
            db.query(Payment)
            .filter(Payment.provider == "razorpay", Payment.gateway_order_id == rzp_order_id)
            .first()
        )

    if payment:
        if event_type in ("payment.captured", "order.paid"):
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="succeeded",
                gateway_payment_id=rzp_payment_id,
                failure_reason=None,
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type, "payment_id": rzp_payment_id},
            )
        elif event_type == "payment.failed":
            reason = payment_entity.get("error_description") or "Razorpay payment failed"
            _apply_webhook_status(
                db=db,
                payment=payment,
                new_status="failed",
                gateway_payment_id=rzp_payment_id,
                failure_reason=reason,
                gateway_ref=event_id,
                summary={"event_id": event_id, "event_type": event_type, "reason": reason},
            )

    webhook_row.processed = True
    webhook_row.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"received": True, "duplicate": False, "event_id": event_id, "event_type": event_type}
