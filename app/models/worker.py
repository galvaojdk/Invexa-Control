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
    role = Column(String, nullable=False) # e.g., Costureira, Acabamento
    daily_rate = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipments = relationship("Shipment", back_populates="worker")

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Float, nullable=False) # Quantidade enviada
    returned_quantity = Column(Float, default=0.0) # Quantidade já retornada
    
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING)
    cost_per_unit = Column(Float, default=0.0) # Valor a pagar por peça
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    worker = relationship("Worker", back_populates="shipments")
    product = relationship("Product")
