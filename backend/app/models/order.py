import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    completed = "completed"
    cancelled = "cancelled"
    disputed = "disputed"
    refunded = "refunded"


VALID_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.pending_payment: {OrderStatus.paid, OrderStatus.cancelled},
    OrderStatus.paid: {OrderStatus.shipped, OrderStatus.cancelled, OrderStatus.disputed, OrderStatus.refunded},
    OrderStatus.shipped: {OrderStatus.delivered, OrderStatus.disputed, OrderStatus.cancelled},
    OrderStatus.delivered: {OrderStatus.completed, OrderStatus.disputed},
    OrderStatus.completed: set(),
    OrderStatus.cancelled: set(),
    OrderStatus.disputed: {OrderStatus.completed, OrderStatus.refunded},
    OrderStatus.refunded: set(),
}


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending_payment, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(Text, nullable=True)
    tracking_number = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    buyer = relationship("User", back_populates="purchases", foreign_keys=[buyer_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    escrow = relationship("Escrow", back_populates="order", uselist=False)
    dispute = relationship("Dispute", back_populates="order", uselist=False)
    refunds = relationship("Refund", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    seller = relationship("User", foreign_keys=[seller_id])
