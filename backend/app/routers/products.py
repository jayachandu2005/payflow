"""Product catalog and admin product management routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, User
from ..schemas import ProductCreateRequest, ProductOut, ProductUpdateRequest
from ..security import require_admin

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=List[ProductOut])
def list_products(
    search: Optional[str] = Query(default=None, max_length=120),
    category: Optional[str] = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """List products with optional search and category filtering."""
    query = db.query(Product)
    if not include_inactive:
        query = query.filter(Product.is_active.is_(True))
    if category and category.lower() != "all":
        query = query.filter(Product.category == category)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(Product.name.ilike(pattern) | Product.description.ilike(pattern))
    return query.order_by(Product.id.asc()).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Fetch single product details by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new catalog product (admin only)."""
    if db.query(Product).filter(Product.slug == payload.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product slug already exists.")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an existing catalog product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product
