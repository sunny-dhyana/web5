import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.email import send_dispute_opened
from app.database import get_db
from app.models.audit import AuditLog
from app.models.dispute import Dispute, DisputeStatus, Message
from app.models.order import Order, OrderStatus, VALID_TRANSITIONS
from app.models.user import User
from app.schemas.dispute import (
    DisputeCreate,
    DisputeResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def build_dispute_response(dispute: Dispute) -> DisputeResponse:
    messages = [
        MessageResponse(
            id=m.id,
            dispute_id=m.dispute_id,
            sender_id=m.sender_id,
            sender_username=m.sender.username if m.sender else None,
            content=m.content,
            created_at=m.created_at,
        )
        for m in dispute.messages
    ]
    return DisputeResponse(
        id=dispute.id,
        order_id=dispute.order_id,
        buyer_id=dispute.buyer_id,
        seller_id=dispute.seller_id,
        buyer_username=dispute.buyer.username if dispute.buyer else None,
        seller_username=dispute.seller.username if dispute.seller else None,
        reason=dispute.reason,
        status=dispute.status,
        admin_notes=dispute.admin_notes,
        resolution=dispute.resolution,
        created_at=dispute.created_at,
        resolved_at=dispute.resolved_at,
        messages=messages,
    )


@router.get("", response_model=list[DisputeResponse])
async def list_disputes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "admin":
        disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
    else:
        disputes = (
            db.query(Dispute)
            .filter(
                (Dispute.buyer_id == current_user.id) | (Dispute.seller_id == current_user.id)
            )
            .order_by(Dispute.created_at.desc())
            .all()
        )
    return [build_dispute_response(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(
    dispute_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    is_participant = dispute.buyer_id == current_user.id or dispute.seller_id == current_user.id
    if not is_participant and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return build_dispute_response(dispute)


@router.post("", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def open_dispute(
    body: DisputeCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == body.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can open a dispute")

    disputable = {OrderStatus.paid, OrderStatus.shipped, OrderStatus.delivered}
    if order.status not in disputable:
        raise HTTPException(
            status_code=400,
            detail=f"Disputes can only be opened for orders in paid, shipped, or delivered status",
        )

    if order.dispute:
        raise HTTPException(status_code=400, detail="A dispute is already open for this order")

    seller_id = order.items[0].seller_id if order.items else None
    if not seller_id:
        raise HTTPException(status_code=400, detail="Cannot determine seller for this order")

    dispute = Dispute(
        order_id=order.id,
        buyer_id=current_user.id,
        seller_id=seller_id,
        reason=body.reason,
        status=DisputeStatus.open,
    )
    db.add(dispute)

    order.status = OrderStatus.disputed
    order.updated_at = datetime.utcnow()

    db.add(AuditLog(
        user_id=current_user.id,
        action="dispute_opened",
        entity_type="dispute",
        details=f"Dispute opened for order #{order.id}",
    ))
    db.commit()
    db.refresh(dispute)

    seller = db.query(User).filter(User.id == seller_id).first()
    if seller:
        background_tasks.add_task(
            send_dispute_opened, current_user.email, seller.email, order.id
        )

    return build_dispute_response(dispute)


@router.post("/{dispute_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    dispute_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    is_participant = dispute.buyer_id == current_user.id or dispute.seller_id == current_user.id
    if not is_participant and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    if dispute.status in (DisputeStatus.resolved_buyer, DisputeStatus.resolved_seller, DisputeStatus.closed):
        raise HTTPException(status_code=400, detail="This dispute has been resolved")

    message = Message(
        dispute_id=dispute.id,
        sender_id=current_user.id,
        content=body.content,
    )
    db.add(message)

    if dispute.status == DisputeStatus.open:
        dispute.status = DisputeStatus.under_review

    db.commit()
    db.refresh(message)

    return MessageResponse(
        id=message.id,
        dispute_id=message.dispute_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        content=message.content,
        created_at=message.created_at,
    )
