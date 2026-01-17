"""Vehicle database models."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Vehicle(Base):
    """Vehicle inventory model."""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vin = Column(String(17), unique=True, nullable=True, index=True)
    make = Column(String(100), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    price = Column(Float, nullable=False, index=True)
    gvwr_class = Column(String(50), nullable=True, index=True)

    # Additional fields from vPIC API
    brake_system_type = Column(String(100), nullable=True)
    primary_fuel_type = Column(String(50), nullable=True)

    # Optional fields
    body_class = Column(String(100), nullable=True)
    trim = Column(String(100), nullable=True)
    transmission = Column(String(100), nullable=True)
    drive_type = Column(String(50), nullable=True)
    engine = Column(String(200), nullable=True)
    color_exterior = Column(String(50), nullable=True)
    color_interior = Column(String(50), nullable=True)
    mileage = Column(Integer, nullable=True)
    condition = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Vehicle(id={self.id}, make={self.make}, model={self.model}, year={self.year})>"

    def to_dict(self):
        """Convert vehicle to dictionary."""
        return {
            "id": self.id,
            "vin": self.vin,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "price": self.price,
            "gvwr_class": self.gvwr_class,
            "brake_system_type": self.brake_system_type,
            "primary_fuel_type": self.primary_fuel_type,
            "body_class": self.body_class,
            "trim": self.trim,
            "transmission": self.transmission,
            "drive_type": self.drive_type,
            "engine": self.engine,
            "color_exterior": self.color_exterior,
            "color_interior": self.color_interior,
            "mileage": self.mileage,
            "condition": self.condition,
            "description": self.description,
        }
