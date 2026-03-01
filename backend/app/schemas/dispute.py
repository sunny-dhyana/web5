from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.dispute import DisputeStatus


class DisputeCreate(BaseModel):
    order_id: int
    reason: str = Field(..., min_length=20, max_length=2000)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: int
    dispute_id: int
    sender_id: int
    sender_username: Optional[str] = None
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DisputeResponse(BaseModel):
    id: int
    order_id: int
    buyer_id: int
    seller_id: int
    buyer_username: Optional[str] = None
    seller_username: Optional[str] = None
    reason: str
    status: DisputeStatus
    admin_notes: Optional[str]
    resolution: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    messages: List[MessageResponse] = []

    model_config = {"from_attributes": True}


class ResolveDisputeRequest(BaseModel):
    resolution: str = Field(..., min_length=10, max_length=2000)
    refund_buyer: bool
    refund_amount: Optional[float] = Field(None, description="Override refund amount. Defaults to full order total if not specified.")
    admin_notes: Optional[str] = Field(None, max_length=1000)
