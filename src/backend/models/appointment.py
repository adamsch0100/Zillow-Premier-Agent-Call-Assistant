from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum
from datetime import datetime

class AppointmentType(enum.Enum):
    IN_PERSON = "in_person"
    VIDEO = "video"

class AppointmentStatus(enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    appointment_type = Column(Enum(AppointmentType), nullable=False)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.REQUESTED)
    scheduled_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String(500))
    fallback_property_id = Column(Integer, ForeignKey("properties.id"))
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    property = relationship("Property", foreign_keys=[property_id], back_populates="appointments")
    fallback_property = relationship("Property", foreign_keys=[fallback_property_id])
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, client_id={self.client_id}, property_id={self.property_id}, status={self.status.value})>"