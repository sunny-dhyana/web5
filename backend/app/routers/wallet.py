from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet, WalletTransaction
from app.schemas.wallet import (
    DepositRequest,
    TransactionListResponse,
    TransactionResponse,
    WalletResponse,
)
from app.services.wallet_service import deposit_funds, get_or_create_wallet

router = APIRouter()


@router.get("", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = get_or_create_wallet(db, current_user.id)
    db.commit()
    return wallet


@router.post("/deposit", response_model=WalletResponse)
async def add_funds(
    body: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deposit_funds(db, current_user.id, body.amount, f"Deposit via {body.payment_method}")
    db.commit()

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    return wallet


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        return TransactionListResponse(items=[], total=0, page=page, per_page=per_page)

    query = db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet.id)
    total = query.count()
    txns = query.order_by(WalletTransaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in txns],
        total=total,
        page=page,
        per_page=per_page,
    )
