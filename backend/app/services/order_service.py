import logging
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.escrow import Escrow, EscrowStatus
from app.models.order import Order, OrderItem, OrderStatus, VALID_TRANSITIONS
from app.models.product import Product
from app.models.refund import Refund, RefundStatus, RefundType
from app.models.user import User
from app.models.audit import AuditLog
from app.models.wallet import Wallet
from app.schemas.order import OrderCreate
from app.services.wallet_service import (
    credit_seller_pending,
    deduct_for_purchase,
    refund_to_buyer,
)

logger = logging.getLogger(__name__)


def validate_transition(current: str, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition order from '{current}' to '{target}'",
        )


def create_order(db: Session, buyer: User, order_data: OrderCreate) -> Order:
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    total_amount = 0.0
    validated_items: List[tuple[Product, int]] = []
    seller_id: int | None = None

    for item_req in order_data.items:
        product = db.query(Product).filter(
            Product.id == item_req.product_id,
            Product.is_active == True,
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product #{item_req.product_id} not found or unavailable")

        if product.seller_id == buyer.id:
            raise HTTPException(status_code=400, detail="You cannot purchase your own products")

        if seller_id is not None and product.seller_id != seller_id:
            raise HTTPException(
                status_code=400,
                detail="All items in an order must be from the same seller. Please place separate orders.",
            )

        seller_id = product.seller_id

        if product.quantity < item_req.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Only {product.quantity} unit(s) available for '{product.title}'",
            )

        validated_items.append((product, item_req.quantity))
        total_amount += product.price * item_req.quantity

    total_amount = round(total_amount, 2)

    # Verify wallet balance before creating order
    wallet = db.query(Wallet).filter(Wallet.user_id == buyer.id).first()
    if not wallet or wallet.balance < total_amount:
        available = wallet.balance if wallet else 0
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ${available:.2f}, Required: ${total_amount:.2f}",
        )

    # Create the order record
    order = Order(
        buyer_id=buyer.id,
        status=OrderStatus.pending_payment,
        total_amount=total_amount,
        shipping_address=order_data.shipping_address,
        notes=order_data.notes,
    )
    db.add(order)
    db.flush()

    # Create order items and reduce inventory
    for product, qty in validated_items:
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            seller_id=product.seller_id,
            quantity=qty,
            unit_price=product.price,
        )
        db.add(item)
        product.quantity -= qty

    # Deduct from buyer's wallet
    deduct_for_purchase(db, buyer.id, total_amount, order.id)

    # Create escrow record
    escrow = Escrow(
        order_id=order.id,
        buyer_id=buyer.id,
        seller_id=seller_id,
        amount=total_amount,
        status=EscrowStatus.held,
    )
    db.add(escrow)

    # Advance order to paid
    order.status = OrderStatus.paid
    order.updated_at = datetime.utcnow()

    db.add(AuditLog(
        user_id=buyer.id,
        action="order_placed",
        entity_type="order",
        entity_id=order.id,
        details=f"Order placed for ${total_amount:.2f}",
    ))

    return order


def release_escrow_to_seller(db: Session, order: Order) -> None:
    escrow = order.escrow
    if not escrow or escrow.status != EscrowStatus.held:
        return

    # Credit each seller based on order items (supports future multi-seller)
    seller_totals: dict[int, float] = {}
    for item in order.items:
        seller_totals[item.seller_id] = seller_totals.get(item.seller_id, 0) + (item.unit_price * item.quantity)

    for sid, amount in seller_totals.items():
        credit_seller_pending(db, sid, round(amount, 2), order.id)

    escrow.status = EscrowStatus.released
    escrow.released_at = datetime.utcnow()


def process_refund(db: Session, order: Order, amount: float, reason: str, initiated_by_id: int) -> Refund:
    escrow = order.escrow
    if not escrow or escrow.status not in (EscrowStatus.held, EscrowStatus.partial_refunded):
        raise HTTPException(status_code=400, detail="No held escrow available for refund")

    refund_type = RefundType.full if amount >= order.total_amount else RefundType.partial

    refund = Refund(
        order_id=order.id,
        initiated_by_id=initiated_by_id,
        amount=amount,
        refund_type=refund_type,
        status=RefundStatus.processed,
        reason=reason,
        processed_at=datetime.utcnow(),
    )
    db.add(refund)

    refund_to_buyer(db, order.buyer_id, amount, order.id)

    if refund_type == RefundType.full:
        escrow.status = EscrowStatus.refunded
    else:
        escrow.status = EscrowStatus.partial_refunded

    escrow.released_at = datetime.utcnow()
    return refund
