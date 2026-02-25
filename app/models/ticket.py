from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    status = Column(String, default="open", index=True) # open, in_progress, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="asc(TicketMessage.created_at)")

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False) # The user (admin or client) who sent
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
