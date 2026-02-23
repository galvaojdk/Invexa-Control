from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from app.core.database import Base
from sqlalchemy.orm import relationship

class WorkerType(Base):
    __tablename__ = "worker_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="worker_types")
    
    workers = relationship("Worker", back_populates="worker_type")

    __table_args__ = (UniqueConstraint('name', 'company_id', name='uix_worker_type_name_company'),)
