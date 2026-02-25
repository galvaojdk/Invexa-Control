from sqlalchemy import Column, Integer, Text, DateTime
from datetime import datetime
from app.core.database import Base

class SystemGuide(Base):
    __tablename__ = "system_guide"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, default="")
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
