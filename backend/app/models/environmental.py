# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Environmental Monitoring Models
Temperature, humidity, airflow tracking
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class EnvironmentalSensor(Base, TenantMixin):
    """Environmental sensors deployed in datacenter"""
    __tablename__ = "environmental_sensors"
    __table_args__ = (
        UniqueConstraint('sensor_id', 'tenant_id', name='idx_environmental_sensors_sensor_id_tenant'),
    )

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=False)

    # Sensor Identification
    sensor_id = Column(String(100), nullable=False, index=True)  # Removed unique - now unique per tenant
    sensor_name = Column(String(200), nullable=False)

    # Type and Capabilities
    sensor_type = Column(String(50))  # temperature, humidity, airflow, power, smoke, water
    manufacturer = Column(String(100))
    model = Column(String(100))

    # Location
    location_description = Column(String(500))
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)

    # Position
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)

    # Specifications
    min_reading = Column(Float)
    max_reading = Column(Float)
    accuracy = Column(Float)
    unit_of_measure = Column(String(20))  # C, F, %, m/s, etc.

    # Thresholds
    warning_threshold_min = Column(Float)
    warning_threshold_max = Column(Float)
    critical_threshold_min = Column(Float)
    critical_threshold_max = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)
    last_reading_at = Column(DateTime, nullable=True)
    last_reading_value = Column(Float, nullable=True)

    # Communication
    ip_address = Column(String(45), nullable=True)
    protocol = Column(String(50))  # SNMP, Modbus, HTTP, etc.

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    installed_at = Column(DateTime, nullable=True)

    # Relationships
    datacenter = relationship("Datacenter", back_populates="environmental_sensors")
    readings = relationship("EnvironmentalReading", back_populates="sensor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EnvironmentalSensor {self.sensor_id} - {self.sensor_type}>"


class EnvironmentalReading(Base, TenantMixin):
    """Time-series environmental readings"""
    __tablename__ = "environmental_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("environmental_sensors.id"), nullable=False, index=True)

    # Reading Data
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))

    # Additional Metrics (for multi-metric sensors)
    secondary_value = Column(Float, nullable=True)
    secondary_unit = Column(String(20), nullable=True)

    # Status
    is_anomaly = Column(Boolean, default=False)
    threshold_breached = Column(String(20), nullable=True)  # warning, critical

    # Correlation with Assets
    correlated_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)

    # Alert Generated
    alert_generated = Column(Boolean, default=False)
    alert_id = Column(String(100), nullable=True)

    # Metadata
    quality_score = Column(Float, default=1.0)  # Data quality indicator
    notes = Column(Text, nullable=True)

    # Relationships
    sensor = relationship("EnvironmentalSensor", back_populates="readings")

    def __repr__(self):
        return f"<EnvironmentalReading {self.sensor_id} @ {self.timestamp}: {self.value}>"
