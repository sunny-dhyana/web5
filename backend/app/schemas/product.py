from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.product import ProductType


class ProductCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    price: float = Field(..., ge=0, le=1_000_000)
    quantity: int = Field(..., ge=0, le=100_000)
    product_type: ProductType = ProductType.shippable
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=2000)
    thank_you_message: Optional[str] = Field(None, max_length=2000)


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    price: Optional[float] = Field(None, ge=0, le=1_000_000)
    quantity: Optional[int] = Field(None, ge=0, le=100_000)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None
    thank_you_message: Optional[str] = Field(None, max_length=2000)


class ProductResponse(BaseModel):
    id: int
    seller_id: int
    title: str
    description: Optional[str]
    price: float
    quantity: int
    product_type: ProductType
    category: Optional[str]
    image_url: Optional[str]
    thank_you_message: Optional[str] = None
    is_active: bool
    created_at: datetime
    seller_username: Optional[str] = None
    seller_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    per_page: int
    pages: int
