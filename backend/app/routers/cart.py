"""Shopping cart management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import CartItem, Product, User
from ..schemas import CartAddRequest, CartItemOut, CartOut, CartUpdateRequest, ProductOut
from ..security import get_current_user

router = APIRouter(prefix="/api/cart", tags=["Cart"])

TAX_RATE = 0.08


def _serialize_cart(db: Session, user_id: int) -> CartOut:
    rows = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.id.asc())
        .all()
    )
    items_out = []
    subtotal_cents = 0
    item_count = 0
    for row in rows:
        if not row.product or not row.product.is_active:
            continue
        line_total = row.product.price_cents * row.quantity
        subtotal_cents += line_total
        item_count += row.quantity
        items_out.append(
            CartItemOut(
                id=row.id,
                product_id=row.product_id,
                quantity=row.quantity,
                product=ProductOut.model_validate(row.product),
                line_total_cents=line_total,
            )
        )
    tax_cents = round(subtotal_cents * TAX_RATE) if subtotal_cents > 0 else 0
    return CartOut(
        items=items_out,
        item_count=item_count,
        subtotal_cents=subtotal_cents,
        tax_cents=tax_cents,
        total_cents=subtotal_cents + tax_cents,
        currency="USD",
    )


@router.get("", response_model=CartOut)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the authenticated user's cart with calculated totals."""
    return _serialize_cart(db, current_user.id)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a product to the cart or increment its quantity."""
    product = db.query(Product).filter(Product.id == payload.product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    if product.stock < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient product stock.")

    existing = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id, CartItem.product_id == payload.product_id)
        .first()
    )
    if existing:
        new_qty = existing.quantity + payload.quantity
        if new_qty > product.stock:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested quantity exceeds stock.")
        existing.quantity = new_qty
    else:
        db.add(CartItem(user_id=current_user.id, product_id=payload.product_id, quantity=payload.quantity))

    db.commit()
    return _serialize_cart(db, current_user.id)


@router.patch("/items/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: int,
    payload: CartUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a cart item's quantity (or remove it when quantity is 0)."""
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    if payload.quantity == 0:
        db.delete(item)
    else:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product and payload.quantity > product.stock:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested quantity exceeds stock.")
        item.quantity = payload.quantity

    db.commit()
    return _serialize_cart(db, current_user.id)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an item from the cart."""
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")
    db.delete(item)
    db.commit()
    return _serialize_cart(db, current_user.id)


@router.delete("", response_model=CartOut)
def clear_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove all items from the user's cart."""
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return _serialize_cart(db, current_user.id)
