from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=True)  # Can be null for unnamed leads
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=False)
    is_qualified = Column(Boolean, default=False)
    source = Column(String(50), nullable=False)  # e.g., "zillow", "realtor.com"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String(1000))
    
    # Relationships
    appointments = relationship("Appointment", back_populates="client")
    search_preferences = relationship("SearchPreference", back_populates="client")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name={self.name}, phone={self.phone})>"