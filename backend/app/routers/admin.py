"""Administrator dashboard and operational audit routes."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Order, Payment, Product, Transaction, User, WebhookEvent
from ..schemas import OrderOut, PaymentSummaryOut, TransactionOut, WebhookEventOut
from ..security import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/stats")
def admin_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate operational metrics for the Admin Dashboard."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    paid_orders = db.query(func.count(Order.id)).filter(Order.status == "paid").scalar() or 0
    failed_orders = db.query(func.count(Order.id)).filter(Order.status == "failed").scalar() or 0
    total_revenue_cents = (
        db.query(func.coalesce(func.sum(Order.total_cents), 0)).filter(Order.status == "paid").scalar() or 0
    )
    total_webhooks = db.query(func.count(WebhookEvent.id)).scalar() or 0
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "failed_orders": failed_orders,
        "total_revenue_cents": int(total_revenue_cents),
        "total_webhooks": total_webhooks,
    }


@router.get("/orders", response_model=List[OrderOut])
def admin_orders(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all orders across all users."""
    orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .order_by(Order.created_at.desc())
        .all()
    )
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/payments", response_model=List[PaymentSummaryOut])
def admin_payments(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all payments across all users."""
    payments = db.query(Payment).order_by(Payment.created_at.desc()).all()
    return [PaymentSummaryOut.model_validate(p) for p in payments]


@router.get("/transactions", response_model=List[TransactionOut])
def admin_transactions(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all sanitized transaction ledger entries."""
    rows = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(200).all()
    return [TransactionOut.model_validate(r) for r in rows]


@router.get("/webhooks", response_model=List[WebhookEventOut])
def admin_webhooks(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List received gateway webhook events and signature validation results."""
    rows = db.query(WebhookEvent).order_by(WebhookEvent.received_at.desc()).limit(100).all()
    return [WebhookEventOut.model_validate(r) for r in rows]
