import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_seller, get_current_user
from app.core.email import send_order_confirmation, send_order_shipped_notification
from app.database import get_db
from app.models.audit import AuditLog
from app.models.order import Order, OrderItem, OrderStatus, VALID_TRANSITIONS
from app.models.user import User
from app.schemas.order import (
    CancelOrderRequest,
    OrderCreate,
    OrderResponse,
    OrderItemResponse,
    ShipOrderRequest,
)
from app.services.order_service import (
    create_order,
    release_escrow_to_seller,
    validate_transition,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def build_order_response(order: Order) -> OrderResponse:
    items = []
    for item in order.items:
        items.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            seller_id=item.seller_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            product_title=item.product.title if item.product else None,
            product_image=item.product.image_url if item.product else None,
        ))
    return OrderResponse(
        id=order.id,
        buyer_id=order.buyer_id,
        buyer_username=order.buyer.username if order.buyer else None,
        status=order.status,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        tracking_number=order.tracking_number,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
    )


@router.get("", response_model=list[OrderResponse])
async def list_my_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Order).filter(Order.buyer_id == current_user.id)

    if status_filter:
        try:
            s = OrderStatus(status_filter)
            query = query.filter(Order.status == s)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    orders = query.order_by(Order.created_at.desc()).all()
    return [build_order_response(o) for o in orders]


@router.get("/seller", response_model=list[OrderResponse])
async def list_seller_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .filter(OrderItem.seller_id == current_user.id)
        .distinct()
    )

    if status_filter:
        try:
            s = OrderStatus(status_filter)
            query = query.filter(Order.status == s)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    orders = query.order_by(Order.created_at.desc()).all()
    return [build_order_response(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_buyer = order.buyer_id == current_user.id
    is_seller = any(item.seller_id == current_user.id for item in order.items)
    is_admin = current_user.role == "admin"

    if not (is_buyer or is_seller or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    return build_order_response(order)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    body: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = create_order(db, current_user, body)
    db.commit()
    db.refresh(order)

    background_tasks.add_task(
        send_order_confirmation, current_user.email, order.id, order.total_amount
    )

    return build_order_response(order)


@router.put("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(
    order_id: int,
    body: ShipOrderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_seller = any(item.seller_id == current_user.id for item in order.items)
    if not is_seller and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    validate_transition(order.status, OrderStatus.shipped)

    order.status = OrderStatus.shipped
    order.tracking_number = body.tracking_number
    order.updated_at = datetime.utcnow()

    db.add(AuditLog(
        user_id=current_user.id,
        action="order_shipped",
        entity_type="order",
        entity_id=order.id,
        details=f"Tracking: {body.tracking_number}",
    ))
    db.commit()
    db.refresh(order)

    background_tasks.add_task(
        send_order_shipped_notification, order.buyer.email, order.id, body.tracking_number
    )

    return build_order_response(order)


@router.put("/{order_id}/confirm-delivery", response_model=OrderResponse)
async def confirm_delivery(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can confirm delivery")

    validate_transition(order.status, OrderStatus.delivered)

    order.status = OrderStatus.delivered
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return build_order_response(order)


@router.put("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can complete an order")

    validate_transition(order.status, OrderStatus.completed)

    order.status = OrderStatus.completed
    order.updated_at = datetime.utcnow()

    release_escrow_to_seller(db, order)

    db.add(AuditLog(
        user_id=current_user.id,
        action="order_completed",
        entity_type="order",
        entity_id=order.id,
    ))
    db.commit()
    db.refresh(order)

    return build_order_response(order)


@router.put("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    body: CancelOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_buyer = order.buyer_id == current_user.id
    is_seller = any(item.seller_id == current_user.id for item in order.items)
    is_admin = current_user.role == "admin"

    if not (is_buyer or is_seller or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    validate_transition(order.status, OrderStatus.cancelled)

    from app.services.order_service import process_refund
    if order.status == OrderStatus.paid:
        process_refund(db, order, order.total_amount, "Order cancelled", current_user.id)

    order.status = OrderStatus.cancelled
    order.updated_at = datetime.utcnow()

    db.add(AuditLog(
        user_id=current_user.id,
        action="order_cancelled",
        entity_type="order",
        entity_id=order.id,
        details=body.reason,
    ))
    db.commit()
    db.refresh(order)

    return build_order_response(order)
