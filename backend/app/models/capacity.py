# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Capacity Management Models
Space, Power, and Cooling capacity tracking
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class CapacityMetrics(Base, TenantMixin):
    """Rack-level capacity metrics snapshot"""
    __tablename__ = "capacity_metrics"

    id = Column(Integer, primary_key=True, index=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=False, index=True)

    # Snapshot timestamp
    measured_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Space Capacity
    total_u_space = Column(Integer)  # Total U positions
    used_u_space = Column(Integer)  # Occupied U positions
    available_u_space = Column(Integer)  # Free U positions
    u_space_utilization_percent = Column(Float)

    # Power Capacity
    total_power_capacity_watts = Column(Float)
    used_power_watts = Column(Float)
    available_power_watts = Column(Float)
    power_utilization_percent = Column(Float)

    # Cooling Capacity
    total_cooling_capacity_btu = Column(Float)
    used_cooling_btu = Column(Float)
    available_cooling_btu = Column(Float)
    cooling_utilization_percent = Column(Float)

    # Network Capacity
    total_network_ports = Column(Integer, default=0)
    used_network_ports = Column(Integer, default=0)
    available_network_ports = Column(Integer, default=0)

    # Weight
    total_weight_kg = Column(Float, default=0)
    max_weight_capacity_kg = Column(Float)

    # Threshold Alerts
    space_warning = Column(Boolean, default=False)
    power_warning = Column(Boolean, default=False)
    cooling_warning = Column(Boolean, default=False)

    # Projected Capacity (based on trends)
    projected_full_date = Column(DateTime, nullable=True)
    days_until_full = Column(Integer, nullable=True)

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CapacityMetrics Rack {self.rack_id} @ {self.measured_at}>"


class PowerMetrics(Base, TenantMixin):
    """Detailed power consumption tracking"""
    __tablename__ = "power_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Target (can be rack, datacenter, or specific asset)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)

    # Measurement
    measured_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Power Metrics
    voltage_v = Column(Float)
    current_a = Column(Float)
    power_watts = Column(Float)
    power_kw = Column(Float)
    apparent_power_va = Column(Float)
    power_factor = Column(Float)

    # Energy
    energy_kwh = Column(Float)  # Cumulative energy consumption

    # Phase (for 3-phase systems)
    phase_1_watts = Column(Float, nullable=True)
    phase_2_watts = Column(Float, nullable=True)
    phase_3_watts = Column(Float, nullable=True)

    # PDU Information
    pdu_id = Column(String(100), nullable=True)
    outlet_number = Column(Integer, nullable=True)

    # Status
    is_anomaly = Column(Boolean, default=False)
    threshold_breached = Column(Boolean, default=False)

    # Metadata
    source = Column(String(50))  # SNMP, IPMI, manual, etc.
    quality_score = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PowerMetrics @ {self.measured_at}: {self.power_watts}W>"


class CoolingMetrics(Base, TenantMixin):
    """Cooling and thermal metrics"""
    __tablename__ = "cooling_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Target
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True, index=True)

    # Measurement
    measured_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Temperature
    temperature_c = Column(Float)
    temperature_f = Column(Float)
    inlet_temp_c = Column(Float, nullable=True)
    outlet_temp_c = Column(Float, nullable=True)
    delta_t = Column(Float, nullable=True)  # Temperature differential

    # Humidity
    relative_humidity_percent = Column(Float)
    dew_point_c = Column(Float, nullable=True)

    # Airflow
    airflow_cfm = Column(Float, nullable=True)  # Cubic feet per minute
    airflow_m3h = Column(Float, nullable=True)  # Cubic meters per hour

    # Cooling Load
    heat_load_btu = Column(Float, nullable=True)
    heat_load_kw = Column(Float, nullable=True)

    # PUE (Power Usage Effectiveness)
    pue = Column(Float, nullable=True)

    # Alerts
    temperature_warning = Column(Boolean, default=False)
    humidity_warning = Column(Boolean, default=False)

    # Metadata
    source = Column(String(50))  # sensor, calculated, manual
    quality_score = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CoolingMetrics @ {self.measured_at}: {self.temperature_c}°C, {self.relative_humidity_percent}%>"
