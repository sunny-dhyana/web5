from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.wallet import TransactionType


class WalletResponse(BaseModel):
    id: int
    user_id: int
    balance: float
    pending_balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, le=10_000, description="Amount to deposit (max $10,000 per transaction)")
    payment_method: str = Field("card", pattern=r"^(card|bank_transfer)$")


class TransactionResponse(BaseModel):
    id: int
    amount: float
    transaction_type: TransactionType
    reference_id: Optional[int]
    reference_type: Optional[str]
    description: Optional[str]
    balance_after: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    from_wallet_id: int = Field(..., description="Source wallet ID")
    to_wallet_id: int = Field(..., description="Destination wallet ID")
    amount: float = Field(..., gt=0, le=10_000)
    note: Optional[str] = Field(None, max_length=200)


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    per_page: int
