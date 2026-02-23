from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint
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
    name = Column(String, index=True)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="categories")
    
    products = relationship("Product", back_populates="category")

    __table_args__ = (UniqueConstraint('name', 'company_id', name='uix_category_name_company'),)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True, nullable=True)
    name = Column(String, index=True) # Descrição Reduzida
    description = Column(String) # Descrição Completa
    unit = Column(String, default="un") # Und, Metro, KG, etc
    current_stock = Column(Float, default=0.0)

    is_composite = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="products")
    
    category = relationship("Category", back_populates="products")
    movements = relationship("Movement", back_populates="product")
    
    # Relationship for composite products
    composition = relationship(
        "ProductComposition",
        foreign_keys="ProductComposition.composite_id",
        backref="composite_product",
        cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint('sku', 'company_id', name='uix_product_sku_company'),)

class ProductComposition(Base):
    __tablename__ = "product_compositions"
    id = Column(Integer, primary_key=True, index=True)
    composite_id = Column(Integer, ForeignKey("products.id"), index=True)
    component_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    # Relationship to get component details
    component = relationship("Product", foreign_keys=[component_id])

class Movement(Base):
    __tablename__ = "movements"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    type = Column(Enum(MovementType))
    reason = Column(String) # compra, venda, ajuste, consumo
    timestamp = Column(DateTime, default=datetime.now)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    product = relationship("Product", back_populates="movements")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sector = Column(String, nullable=True) # Setor de destino ou origem
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    action = Column(String)
    resource_type = Column(String) # product, category, movement
    resource_id = Column(Integer, nullable=True)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    
    user = relationship("User")


