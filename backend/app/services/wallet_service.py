from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.wallet import Wallet, WalletTransaction, TransactionType


def get_or_create_wallet(db: Session, user_id: int) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0.0, pending_balance=0.0)
        db.add(wallet)
        db.flush()
    return wallet


def deposit_funds(db: Session, user_id: int, amount: float, description: str | None = None) -> WalletTransaction:
    wallet = get_or_create_wallet(db, user_id)
    wallet.balance = round(wallet.balance + amount, 2)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user_id,
        amount=amount,
        transaction_type=TransactionType.deposit,
        description=description or f"Deposit of ${amount:.2f}",
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn


def deduct_for_purchase(db: Session, user_id: int, amount: float, order_id: int) -> WalletTransaction:
    wallet = get_or_create_wallet(db, user_id)

    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient wallet balance. Available: ${wallet.balance:.2f}, Required: ${amount:.2f}",
        )

    wallet.balance = round(wallet.balance - amount, 2)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user_id,
        amount=-amount,
        transaction_type=TransactionType.purchase,
        reference_id=order_id,
        reference_type="order",
        description=f"Purchase — Order #{order_id}",
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn


def credit_seller_pending(db: Session, seller_id: int, amount: float, order_id: int) -> WalletTransaction:
    wallet = get_or_create_wallet(db, seller_id)
    wallet.pending_balance = round(wallet.pending_balance + amount, 2)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=seller_id,
        amount=amount,
        transaction_type=TransactionType.escrow_release,
        reference_id=order_id,
        reference_type="order",
        description=f"Sale proceeds — Order #{order_id}",
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn


def refund_to_buyer(db: Session, buyer_id: int, amount: float, order_id: int) -> WalletTransaction:
    wallet = get_or_create_wallet(db, buyer_id)
    wallet.balance = round(wallet.balance + amount, 2)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=buyer_id,
        amount=amount,
        transaction_type=TransactionType.escrow_refund,
        reference_id=order_id,
        reference_type="order",
        description=f"Refund — Order #{order_id}",
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn


def process_payout_deduction(db: Session, seller_id: int, amount: float, payout_id: int) -> WalletTransaction:
    wallet = get_or_create_wallet(db, seller_id)

    if wallet.pending_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient pending balance. Available: ${wallet.pending_balance:.2f}",
        )

    wallet.pending_balance = round(wallet.pending_balance - amount, 2)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=seller_id,
        amount=-amount,
        transaction_type=TransactionType.payout,
        reference_id=payout_id,
        reference_type="payout",
        description=f"Payout #{payout_id}",
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn


def admin_adjust_balance(db: Session, user_id: int, amount: float, description: str) -> WalletTransaction:
    wallet = get_or_create_wallet(db, user_id)
    new_balance = round(wallet.balance + amount, 2)

    if new_balance < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment would result in a negative balance",
        )

    wallet.balance = new_balance

    txn = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user_id,
        amount=amount,
        transaction_type=TransactionType.admin_adjustment,
        description=description,
        balance_after=wallet.balance,
    )
    db.add(txn)
    return txn
