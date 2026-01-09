# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Maintenance and Predictive Analytics Models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class MaintenanceType(str, enum.Enum):
    """Types of maintenance"""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"
    UPGRADE = "upgrade"
    REPLACEMENT = "replacement"


class MaintenanceStatus(str, enum.Enum):
    """Maintenance record status"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class MaintenancePriority(str, enum.Enum):
    """Maintenance priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MaintenanceRecord(Base, TenantMixin):
    """Maintenance history and scheduling"""
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    # Maintenance Details
    maintenance_type = Column(SQLEnum(MaintenanceType), nullable=False)
    status = Column(SQLEnum(MaintenanceStatus), default=MaintenanceStatus.SCHEDULED)
    priority = Column(SQLEnum(MaintenancePriority), default=MaintenancePriority.MEDIUM)

    # Scheduling
    scheduled_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Duration and Effort
    estimated_duration_hours = Column(Float)
    actual_duration_hours = Column(Float)
    downtime_hours = Column(Float)

    # Personnel
    assigned_to = Column(String(200))
    performed_by = Column(String(200))

    # Details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    work_performed = Column(Text)

    # Parts and Costs
    parts_replaced = Column(JSON, default=[])  # List of part numbers/descriptions
    parts_cost = Column(Float)
    labor_cost = Column(Float)
    total_cost = Column(Float)

    # Outcome
    issue_resolved = Column(Boolean, default=False)
    follow_up_required = Column(Boolean, default=False)
    follow_up_notes = Column(Text)

    # MTTR Tracking
    failure_detected_at = Column(DateTime, nullable=True)
    mttr_minutes = Column(Float, nullable=True)  # Mean Time To Repair

    # Documentation
    before_photos = Column(JSON, default=[])
    after_photos = Column(JSON, default=[])
    documentation_urls = Column(JSON, default=[])

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="maintenance_records")

    def __repr__(self):
        return f"<MaintenanceRecord {self.id} - {self.title}>"


class MaintenancePrediction(Base, TenantMixin):
    """AI-powered predictive maintenance predictions"""
    __tablename__ = "maintenance_predictions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    # Prediction Details
    prediction_date = Column(DateTime, default=datetime.utcnow, index=True)
    predicted_failure_date = Column(DateTime, nullable=True)
    confidence_score = Column(Float)  # 0.0 to 1.0

    # Failure Type
    failure_type = Column(String(100))  # disk, psu, fan, network, etc.
    failure_severity = Column(String(20))  # critical, high, medium, low

    # Indicators
    indicators = Column(JSON, default={})  # Temperature trends, error rates, etc.

    # Recommendations
    recommended_action = Column(Text)
    estimated_mttr_hours = Column(Float)
    replacement_parts = Column(JSON, default=[])

    # Model Information
    ml_model_version = Column(String(50))
    training_data_points = Column(Integer)

    # Outcome Tracking
    prediction_verified = Column(Boolean, nullable=True)
    actual_failure_date = Column(DateTime, nullable=True)
    action_taken = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="maintenance_predictions")

    def __repr__(self):
        return f"<MaintenancePrediction for Asset {self.asset_id} - {self.failure_type}>"
