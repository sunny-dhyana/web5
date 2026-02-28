import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.core.email import send_dispute_resolved, send_refund_notification
from app.database import get_db
from app.models.audit import AuditLog
from app.models.dispute import Dispute, DisputeStatus
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.dispute import ResolveDisputeRequest
from app.schemas.order import OrderResponse
from app.schemas.user import UserResponse
from app.services.order_service import process_refund, release_escrow_to_seller
from app.services.wallet_service import admin_adjust_balance

router = APIRouter()
logger = logging.getLogger(__name__)


class WalletAdjustRequest(BaseModel):
    amount: float = Field(..., description="Positive to credit, negative to debit")
    description: str = Field(..., min_length=5, max_length=500)


class AdminUserResponse(UserResponse):
    wallet_balance: Optional[float] = None
    wallet_pending: Optional[float] = None


@router.get("/users", response_model=list[UserResponse])
async def list_all_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search:
        like = f"%{search}%"
        from sqlalchemy import or_
        query = query.filter(or_(User.email.ilike(like), User.username.ilike(like)))

    users = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return users


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wallet = user.wallet
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_frozen": user.is_frozen,
        "created_at": user.created_at,
        "wallet_balance": wallet.balance if wallet else 0,
        "wallet_pending": wallet.pending_balance if wallet else 0,
    }


@router.put("/users/{user_id}/freeze")
async def freeze_account(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot freeze administrator accounts")

    user.is_frozen = True
    db.add(AuditLog(
        user_id=admin.id,
        action="account_frozen",
        entity_type="user",
        entity_id=user.id,
    ))
    db.commit()
    return {"message": f"Account {user.username} has been frozen"}


@router.put("/users/{user_id}/unfreeze")
async def unfreeze_account(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_frozen = False
    db.add(AuditLog(
        user_id=admin.id,
        action="account_unfrozen",
        entity_type="user",
        entity_id=user.id,
    ))
    db.commit()
    return {"message": f"Account {user.username} has been unfrozen"}


@router.put("/users/{user_id}/verify")
async def manually_verify_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": f"User {user.username} has been verified"}


@router.post("/users/{user_id}/wallet/adjust")
async def adjust_wallet(
    user_id: int,
    body: WalletAdjustRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    admin_adjust_balance(db, user_id, body.amount, body.description)

    db.add(AuditLog(
        user_id=admin.id,
        action="wallet_adjusted",
        entity_type="user",
        entity_id=user_id,
        details=f"${body.amount:+.2f} — {body.description}",
    ))
    db.commit()

    return {"message": f"Wallet adjusted by ${body.amount:+.2f}", "description": body.description}


@router.get("/orders")
async def list_all_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Order)

    if status_filter:
        try:
            s = OrderStatus(status_filter)
            query = query.filter(Order.status == s)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    from app.routers.orders import build_order_response
    return {
        "items": [build_order_response(o) for o in orders],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/disputes")
async def list_all_disputes(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
    from app.routers.disputes import build_dispute_response
    return [build_dispute_response(d) for d in disputes]


@router.put("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: int,
    body: ResolveDisputeRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.status in (DisputeStatus.resolved_buyer, DisputeStatus.resolved_seller):
        raise HTTPException(status_code=400, detail="This dispute is already resolved")

    order = dispute.order
    now = datetime.utcnow()

    if body.refund_buyer:
        process_refund(db, order, order.total_amount, body.resolution, admin.id)
        order.status = OrderStatus.refunded
        dispute.status = DisputeStatus.resolved_buyer

        background_tasks.add_task(
            send_refund_notification, dispute.buyer.email, order.id, order.total_amount
        )
    else:
        release_escrow_to_seller(db, order)
        order.status = OrderStatus.completed
        dispute.status = DisputeStatus.resolved_seller

    order.updated_at = now
    dispute.resolution = body.resolution
    dispute.admin_notes = body.admin_notes
    dispute.resolved_by_id = admin.id
    dispute.resolved_at = now

    db.add(AuditLog(
        user_id=admin.id,
        action="dispute_resolved",
        entity_type="dispute",
        entity_id=dispute.id,
        details=f"refund_buyer={body.refund_buyer}",
    ))
    db.commit()

    background_tasks.add_task(
        send_dispute_resolved,
        dispute.buyer.email if body.refund_buyer else dispute.seller.email,
        order.id,
        body.resolution,
    )

    from app.routers.disputes import build_dispute_response
    return build_dispute_response(dispute)


@router.get("/stats")
async def get_platform_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.product import Product
    from app.models.wallet import Wallet

    total_users = db.query(User).count()
    total_products = db.query(Product).filter(Product.is_active == True).count()
    total_orders = db.query(Order).count()
    open_disputes = db.query(Dispute).filter(
        Dispute.status.in_([DisputeStatus.open, DisputeStatus.under_review])
    ).count()

    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "open_disputes": open_disputes,
    }
