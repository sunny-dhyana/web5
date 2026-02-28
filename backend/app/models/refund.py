import enum
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class RefundType(str, enum.Enum):
    full = "full"
    partial = "partial"


class RefundStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    initiated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    refund_type = Column(Enum(RefundType), nullable=False)
    status = Column(Enum(RefundStatus), default=RefundStatus.pending, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="refunds")
    initiated_by = relationship("User", foreign_keys=[initiated_by_id])
