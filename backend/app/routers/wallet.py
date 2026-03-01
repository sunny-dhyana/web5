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
    TransferRequest,
    WalletResponse,
)
from app.models.wallet import TransactionType
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


@router.post("/transfer", response_model=WalletResponse)
async def transfer_funds(
    body: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from_wallet = db.query(Wallet).filter(Wallet.id == body.from_wallet_id).first()
    if not from_wallet:
        raise HTTPException(status_code=404, detail="Source wallet not found")

    to_wallet = db.query(Wallet).filter(Wallet.id == body.to_wallet_id).first()
    if not to_wallet:
        raise HTTPException(status_code=404, detail="Destination wallet not found")

    if from_wallet.balance < body.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ${from_wallet.balance:.2f}",
        )

    from_balance = from_wallet.balance
    to_balance = to_wallet.balance

    from_wallet.balance = round(from_balance - body.amount, 2)
    to_wallet.balance = round(to_balance + body.amount, 2)

    note = body.note or f"Transfer of ${body.amount:.2f}"
    from app.models.wallet import WalletTransaction
    db.add(WalletTransaction(
        wallet_id=from_wallet.id,
        user_id=current_user.id,
        amount=-body.amount,
        transaction_type=TransactionType.transfer,
        description=note,
        balance_after=from_wallet.balance,
    ))
    db.add(WalletTransaction(
        wallet_id=to_wallet.id,
        user_id=to_wallet.user_id,
        amount=body.amount,
        transaction_type=TransactionType.transfer,
        description=note,
        balance_after=to_wallet.balance,
    ))

    db.commit()
    db.refresh(from_wallet)
    return from_wallet


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_user_id = user_id if user_id is not None else current_user.id
    wallet = db.query(Wallet).filter(Wallet.user_id == target_user_id).first()
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
