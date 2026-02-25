from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class OPStatus(enum.Enum):
    DRAFT = "rascunho"
    RELEASED = "liberada"
    IN_PROGRESS = "em_producao"
    COMPLETED = "concluida"
    CANCELLED = "cancelada"

class ProductionOrder(Base):
    __tablename__ = "production_orders"

    id = Column(Integer, primary_key=True, index=True)
    op_number = Column(String, index=True, nullable=False) # e.g. OP-001
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False) # The finished good to produce
    
    expected_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, default=0.0)
    
    status = Column(Enum(OPStatus), default=OPStatus.DRAFT)
    
    start_date = Column(DateTime, nullable=True)    
    end_date = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    company = relationship("Company")
    product = relationship("Product")
    
    materials = relationship("OPMaterial", back_populates="op", cascade="all, delete-orphan")

class OPMaterial(Base):
    __tablename__ = "op_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    op_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    expected_quantity = Column(Float, nullable=False)
    consumed_quantity = Column(Float, default=0.0)
    
    op = relationship("ProductionOrder", back_populates="materials")
    component = relationship("Product")
