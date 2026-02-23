from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.models.inventory import Product

class ShipmentStatus(enum.Enum):
    PENDING = "pendente"
    PARTIAL = "parcial"
    COMPLETED = "finalizado"
    CANCELLED = "cancelado"

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    tax_id = Column(String, nullable=True) # CPF/CNPJ
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(String, nullable=True) # Deprecated, use worker_type
    
    address = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    
    worker_type_id = Column(Integer, ForeignKey("worker_types.id"), nullable=True)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="workers")
    
    daily_rate = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    worker_type = relationship("WorkerType", back_populates="workers")
    shipments = relationship("Shipment", back_populates="worker")

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    quantity = Column(Float, nullable=False) # Quantidade enviada
    returned_quantity = Column(Float, default=0.0) # Quantidade já retornada
    
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING)
    cost_per_unit = Column(Float, default=0.0) # Valor a pagar por peça
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    notes = Column(Text, nullable=True)

    worker = relationship("Worker", back_populates="shipments")
    product = relationship("Product")
