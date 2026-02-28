import asyncio
import logging
import secrets
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_seller
from app.core.email import send_payout_notification
from app.database import get_db
from app.models.payout import Payout, PayoutStatus
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.payout import PayoutListResponse, PayoutRequest, PayoutResponse
from app.services.wallet_service import process_payout_deduction

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_payout_async(payout_id: int, seller_email: str, amount: float, database_url: str):
    """Background task to simulate payout processing."""
    await asyncio.sleep(3)  # Simulate processing delay

    from app.database import SessionLocal
    from app.models.payout import Payout, PayoutStatus

    db = SessionLocal()
    try:
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        if payout and payout.status == PayoutStatus.processing:
            payout.status = PayoutStatus.completed
            payout.completed_at = datetime.utcnow()
            payout.reference = f"PAY-{secrets.token_hex(8).upper()}"
            db.commit()
            logger.info(f"Payout #{payout_id} completed. Ref: {payout.reference}")

            await send_payout_notification(seller_email, amount, "completed")
    except Exception as e:
        logger.error(f"Payout processing error for #{payout_id}: {e}")
    finally:
        db.close()


@router.get("", response_model=PayoutListResponse)
async def list_payouts(
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    payouts = (
        db.query(Payout)
        .filter(Payout.seller_id == current_user.id)
        .order_by(Payout.created_at.desc())
        .all()
    )
    return PayoutListResponse(
        items=[PayoutResponse.model_validate(p) for p in payouts],
        total=len(payouts),
    )


@router.post("", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
async def request_payout(
    body: PayoutRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet or wallet.pending_balance < body.amount:
        available = wallet.pending_balance if wallet else 0
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient pending balance. Available: ${available:.2f}",
        )

    payout = Payout(
        seller_id=current_user.id,
        amount=body.amount,
        status=PayoutStatus.processing,
        method=body.method,
        notes=body.notes,
        processed_at=datetime.utcnow(),
    )
    db.add(payout)
    db.flush()

    process_payout_deduction(db, current_user.id, body.amount, payout.id)
    db.commit()
    db.refresh(payout)

    from app.config import settings
    background_tasks.add_task(
        process_payout_async,
        payout.id,
        current_user.email,
        body.amount,
        settings.database_url,
    )

    return PayoutResponse.model_validate(payout)


@router.get("/{payout_id}", response_model=PayoutResponse)
async def get_payout(
    payout_id: int,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    payout = db.query(Payout).filter(
        Payout.id == payout_id,
        Payout.seller_id == current_user.id,
    ).first()

    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    return PayoutResponse.model_validate(payout)
