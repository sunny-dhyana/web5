import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class DisputeStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    resolved_buyer = "resolved_buyer"
    resolved_seller = "resolved_seller"
    closed = "closed"


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(DisputeStatus), default=DisputeStatus.open, nullable=False)
    admin_notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="dispute")
    buyer = relationship("User", back_populates="disputes_as_buyer", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="disputes_as_seller", foreign_keys=[seller_id])
    messages = relationship("Message", back_populates="dispute", cascade="all, delete-orphan", order_by="Message.created_at")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    dispute_id = Column(Integer, ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dispute = relationship("Dispute", back_populates="messages")
    sender = relationship("User", back_populates="messages")
