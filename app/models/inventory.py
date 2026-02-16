from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class MovementType(enum.Enum):
    IN = "entrada"
    OUT = "saida"

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, index=True) # Descrição Reduzida
    description = Column(String) # Descrição Completa
    unit = Column(String, default="un") # Und, Metro, KG, etc
    current_stock = Column(Float, default=0.0)

    is_composite = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    category = relationship("Category", back_populates="products")
    movements = relationship("Movement", back_populates="product")

class Movement(Base):
    __tablename__ = "movements"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    type = Column(Enum(MovementType))
    reason = Column(String) # compra, venda, ajuste, consumo
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="movements")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sector = Column(String, nullable=True) # Setor de destino ou origem
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    resource_type = Column(String) # product, category, movement
    resource_id = Column(Integer, nullable=True)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")


