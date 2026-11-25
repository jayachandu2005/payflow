"""Checkout and order management routes."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import CartItem, Order, OrderItem, Payment, User
from ..schemas import CheckoutCustomerInfo, OrderOut
from ..security import get_current_user
from ..services.payment_service import cancel_payment_for_order
from .cart import TAX_RATE

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def _generate_order_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = uuid.uuid4().hex[:6].upper()
    return f"PF-{date_part}-{rand_part}"


def _load_order(db: Session, order_id: int) -> Order | None:
    return (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.id == order_id)
        .first()
    )


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout_create_order(
    payload: CheckoutCustomerInfo,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert the authenticated user's cart into a persistent Order."""
    cart_items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == current_user.id)
        .all()
    )
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your shopping cart is empty.",
        )

    subtotal_cents = 0
    order_items_to_create: list[OrderItem] = []
    for cart_item in cart_items:
        product = cart_item.product
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more products in your cart are unavailable.",
            )
        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}.",
            )
        line_total = product.price_cents * cart_item.quantity
        subtotal_cents += line_total
        order_items_to_create.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price_cents=product.price_cents,
                quantity=cart_item.quantity,
                line_total_cents=line_total,
            )
        )

    tax_cents = round(subtotal_cents * TAX_RATE)
    total_cents = subtotal_cents + tax_cents

    order = Order(
        order_number=_generate_order_number(),
        user_id=current_user.id,
        status="pending",
        subtotal_cents=subtotal_cents,
        tax_cents=tax_cents,
        total_cents=total_cents,
        currency="USD",
        customer_name=payload.customer_name.strip(),
        customer_email=payload.customer_email.strip().lower(),
        customer_phone=payload.customer_phone.strip(),
        shipping_address=payload.shipping_address.strip(),
        shipping_city=payload.shipping_city.strip(),
        shipping_postal_code=payload.shipping_postal_code.strip(),
        shipping_country=payload.shipping_country.strip(),
    )
    db.add(order)
    db.flush()

    for oi in order_items_to_create:
        oi.order_id = order.id
        db.add(oi)

    # Clear cart once order is persisted
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()

    created = _load_order(db, order.id)
    return OrderOut.model_validate(created)


@router.get("", response_model=List[OrderOut])
def list_my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List orders belonging to the authenticated user."""
    orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.payments))
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single order (restricted to owner or admin)."""
    order = _load_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order.")
    return OrderOut.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an unpaid order."""
    order = _load_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this order.")
    if order.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid orders cannot be cancelled here.")
    for payment in list(order.payments):
        if payment.status not in ("succeeded", "cancelled"):
            cancel_payment_for_order(db=db, payment=payment, reason="Order cancelled by customer")
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(_load_order(db, order.id))
