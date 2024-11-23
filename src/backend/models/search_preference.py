from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime

class SearchPreference(Base):
    __tablename__ = "search_preferences"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    min_price = Column(Float)
    max_price = Column(Float)
    min_bedrooms = Column(Integer)
    min_bathrooms = Column(Float)
    min_square_feet = Column(Integer)
    preferred_zip_codes = Column(JSON)  # List of preferred ZIP codes
    preferred_cities = Column(JSON)  # List of preferred cities
    property_types = Column(JSON)  # List of preferred property types
    search_radius = Column(Float)  # Search radius in miles
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String(1000))
    
    # Relationships
    client = relationship("Client", back_populates="search_preferences")
    
    def __repr__(self):
        return f"<SearchPreference(id={self.id}, client_id={self.client_id})>"