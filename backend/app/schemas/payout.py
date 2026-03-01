from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.payout import PayoutStatus


class PayoutRequest(BaseModel):
    amount: float = Field(...)
    method: str = Field("bank_transfer", pattern=r"^(bank_transfer|paypal|crypto)$")
    notes: Optional[str] = Field(None, max_length=500)


class PayoutResponse(BaseModel):
    id: int
    seller_id: int
    amount: float
    status: PayoutStatus
    method: str
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PayoutListResponse(BaseModel):
    items: List[PayoutResponse]
    total: int
