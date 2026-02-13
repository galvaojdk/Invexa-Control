from sqlalchemy import Column, Integer, String
from app.core.database import Base
from sqlalchemy.orm import relationship

class WorkerType(Base):
    __tablename__ = "worker_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    workers = relationship("Worker", back_populates="worker_type")
