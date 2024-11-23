from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum
from datetime import datetime

class PropertyStatus(enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    zillow_id = Column(String(50), unique=True, nullable=True)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    price = Column(Float, nullable=False)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    square_feet = Column(Integer)
    property_type = Column(String(50))  # e.g., "single_family", "condo", "townhouse"
    year_built = Column(Integer)
    status = Column(Enum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(String(2000))
    
    # Relationships
    appointments = relationship("Appointment", foreign_keys="Appointment.property_id", back_populates="property")
    
    def __repr__(self):
        return f"<Property(id={self.id}, address={self.address}, status={self.status.value})>"