import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.deps import get_current_seller, get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()

CATEGORIES = [
    "Electronics", "Accessories", "Clothing", "Food & Beverage",
    "Education", "Software", "Books", "Home & Garden", "Sports", "Other",
]


def build_product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        seller_id=product.seller_id,
        title=product.title,
        description=product.description,
        price=product.price,
        quantity=product.quantity,
        product_type=product.product_type,
        category=product.category,
        image_url=product.image_url,
        thank_you_message=product.thank_you_message,
        is_active=product.is_active,
        created_at=product.created_at,
        seller_username=product.seller.username if product.seller else None,
        seller_name=product.seller.full_name if product.seller else None,
    )


@router.get("", response_model=ProductListResponse)
async def list_products(
    search: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = Query(None, max_length=100),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Product.title.ilike(like), Product.description.ilike(like))
        )

    if category:
        query = query.filter(Product.category == category)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    total = query.count()
    products = query.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return ProductListResponse(
        items=[build_product_response(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/search")
async def advanced_search(
    q: str = Query(..., min_length=1, max_length=500),
    db: Session = Depends(get_db),
):
    stmt = text(
        f"SELECT id, title, description, price, quantity, category, seller_id "
        f"FROM products "
        f"WHERE is_active = 1 AND (title LIKE '%{q}%' OR description LIKE '%{q}%') "
        f"LIMIT 20"
    )
    rows = db.execute(stmt).fetchall()
    return [
        {"id": r[0], "title": r[1], "description": r[2],
         "price": r[3], "quantity": r[4], "category": r[5], "seller_id": r[6]}
        for r in rows
    ]


@router.get("/categories")
async def get_categories():
    return {"categories": CATEGORIES}


@router.get("/{product_id}/similar")
async def similar_products(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    stmt = text(
        f"SELECT id, title, description, price, quantity, category, seller_id "
        f"FROM products "
        f"WHERE is_active = 1 AND category = '{product.category}' AND id != {product_id} "
        f"LIMIT 6"
    )
    rows = db.execute(stmt).fetchall()
    return [
        {"id": r[0], "title": r[1], "description": r[2],
         "price": r[3], "quantity": r[4], "category": r[5], "seller_id": r[6]}
        for r in rows
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return build_product_response(product)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    product = Product(
        seller_id=current_user.id,
        title=body.title,
        description=body.description,
        price=body.price,
        quantity=body.quantity,
        product_type=body.product_type,
        category=body.category,
        image_url=body.image_url,
        thank_you_message=body.thank_you_message,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return build_product_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this product")

    if body.title is not None:
        product.title = body.title
    if body.description is not None:
        product.description = body.description
    if body.price is not None:
        product.price = body.price
    if body.quantity is not None:
        product.quantity = body.quantity
    if body.category is not None:
        product.category = body.category
    if body.image_url is not None:
        product.image_url = body.image_url
    if body.is_active is not None:
        product.is_active = body.is_active
    if body.thank_you_message is not None:
        product.thank_you_message = body.thank_you_message

    db.commit()
    db.refresh(product)
    return build_product_response(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this product")

    product.is_active = False
    db.commit()
