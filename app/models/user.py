from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Multi-tenancy
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", back_populates="users")
    
    # Premium Fields
    is_premium = Column(Boolean, default=False)
    subscription_status = Column(String, default="inactive") # inactive, active, expired, canceled
    subscription_plan = Column(String, default="free") # free, monthly, annual
    subscription_end_date = Column(DateTime, nullable=True)
    full_name = Column(String, nullable=True)
