from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    logo_data = Column(String, nullable=True) # Base64 image data
    created_at = Column(DateTime, default=datetime.now)
    
    users = relationship("User", back_populates="company")
    categories = relationship("Category", back_populates="company")
    products = relationship("Product", back_populates="company")
    workers = relationship("Worker", back_populates="company")
    worker_types = relationship("WorkerType", back_populates="company")
