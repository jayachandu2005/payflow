"""Payment initiation, authoritative verification, cancellation, and history routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..database import get_db
from ..models import Order, Payment, Transaction, User
from ..schemas import (
    GatewayMethodInfo,
    OrderOut,
    PaymentCancelRequest,
    PaymentConfigOut,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentSummaryOut,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    TransactionOut,
)
from ..security import get_current_user
from ..services.payment_service import (
    cancel_payment_for_order,
    initiate_payment_for_order,
    verify_payment_authoritatively,
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("/config", response_model=PaymentConfigOut)
def get_payment_config():
    """Return public gateway configuration (publishable keys only, never secrets)."""
    settings = get_settings()
    methods = [
        GatewayMethodInfo(
            provider="razorpay",
            payment_method="razorpay_checkout",
            label="Razorpay Standard Checkout (Cards / OTP / UPI / Netbanking)",
            description="Official Razorpay Test Mode modal with simulated ACS Bank 3DS OTP page.",
            configured=settings.razorpay_configured,
            supports_3ds_otp=True,
            currency="INR",
        ),
        GatewayMethodInfo(
            provider="stripe",
            payment_method="card",
            label="Stripe Card Elements (3D Secure 2 Challenge)",
            description="Official Stripe Elements card form triggering Stripe's hosted 3DS2 challenge modal.",
            configured=settings.stripe_configured,
            supports_3ds_otp=True,
            currency="USD",
        ),
        GatewayMethodInfo(
            provider="stripe",
            payment_method="stripe_checkout",
            label="Stripe Hosted Checkout Page",
            description="Redirects to Stripe's official hosted checkout.stripe.com payment page.",
            configured=settings.stripe_configured,
            supports_3ds_otp=True,
            currency="USD",
        ),
    ]
    return PaymentConfigOut(
        stripe_configured=settings.stripe_configured,
        stripe_publishable_key=settings.STRIPE_PUBLISHABLE_KEY if settings.stripe_configured else None,
        razorpay_configured=settings.razorpay_configured,
        razorpay_key_id=settings.RAZORPAY_KEY_ID if settings.razorpay_configured else None,
        usd_to_inr_rate=settings.USD_TO_INR_RATE,
        available_methods=methods,
    )


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
def initiate_payment(
    payload: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a payment request with the selected official gateway SDK."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == payload.order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this order.")

    payment, gateway_payload = initiate_payment_for_order(
        db=db,
        order=order,
        user_id=current_user.id,
        provider=payload.provider,
        payment_method=payload.payment_method,
        idempotency_key=payload.idempotency_key,
    )
    db.refresh(order)
    return PaymentInitiateResponse(
        payment=PaymentSummaryOut.model_validate(payment),
        order_status=order.status,
        gateway_payload=gateway_payload,
    )


@router.post("/verify", response_model=PaymentVerifyResponse)
def verify_payment(
    payload: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authoritatively verify payment status directly with the gateway API."""
    payment = db.query(Payment).filter(Payment.id == payload.payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this payment.")

    updated_payment, order, verification = verify_payment_authoritatively(
        db=db,
        payment=payment,
        gateway_payment_id=payload.gateway_payment_id,
        gateway_order_id=payload.gateway_order_id,
        gateway_signature=payload.gateway_signature,
        source="verification",
    )
    loaded_order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.id == order.id)
        .first()
    )
    return PaymentVerifyResponse(
        payment=PaymentSummaryOut.model_validate(updated_payment),
        order=OrderOut.model_validate(loaded_order),
        verified_authoritatively=True,
        gateway_status=verification.gateway_status,
        message=verification.message,
    )


@router.post("/cancel", response_model=PaymentVerifyResponse)
def cancel_payment(
    payload: PaymentCancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an unpaid payment attempt and synchronize order status."""
    payment = db.query(Payment).filter(Payment.id == payload.payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this payment.")

    updated_payment, order, result = cancel_payment_for_order(db=db, payment=payment, reason=payload.reason)
    loaded_order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.id == order.id)
        .first()
    )
    return PaymentVerifyResponse(
        payment=PaymentSummaryOut.model_validate(updated_payment),
        order=OrderOut.model_validate(loaded_order),
        verified_authoritatively=True,
        gateway_status=result.gateway_status,
        message=result.message,
    )


@router.get("/transactions", response_model=List[TransactionOut])
def list_my_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List transaction audit logs for the authenticated user's orders."""
    rows = (
        db.query(Transaction)
        .join(Order, Transaction.order_id == Order.id)
        .filter(Order.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return [TransactionOut.model_validate(row) for row in rows]


@router.get("/{payment_id}", response_model=PaymentSummaryOut)
def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single payment summary."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this payment.")
    return PaymentSummaryOut.model_validate(payment)
