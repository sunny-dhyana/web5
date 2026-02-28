from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, le=1000)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=500)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    seller_id: int
    quantity: int
    unit_price: float
    product_title: Optional[str] = None
    product_image: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    buyer_username: Optional[str] = None
    status: OrderStatus
    total_amount: float
    shipping_address: Optional[str]
    tracking_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class ShipOrderRequest(BaseModel):
    tracking_number: str = Field(..., min_length=1, max_length=255)


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
