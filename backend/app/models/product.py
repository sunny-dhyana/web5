import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ProductType(str, enum.Enum):
    digital = "digital"
    shippable = "shippable"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    product_type = Column(Enum(ProductType), default=ProductType.shippable, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    image_url = Column(String(2000), nullable=True)
    thank_you_message = Column(String(2000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    seller = relationship("User", back_populates="products", foreign_keys=[seller_id])
    order_items = relationship("OrderItem", back_populates="product")
