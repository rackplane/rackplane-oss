# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Maintenance Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.maintenance import MaintenanceType, MaintenanceStatus, MaintenancePriority


class MaintenanceCreate(BaseModel):
    asset_id: int
    maintenance_type: MaintenanceType
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    title: str
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    assigned_to: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    status: Optional[MaintenanceStatus] = None
    work_performed: Optional[str] = None
    issue_resolved: Optional[bool] = None
    parts_cost: Optional[float] = None
    labor_cost: Optional[float] = None


class PredictionResponse(BaseModel):
    id: int
    asset_id: int
    prediction_date: datetime
    predicted_failure_date: Optional[datetime]
    confidence_score: float
    failure_type: str
    failure_severity: str
    recommended_action: str

    class Config:
        from_attributes = True
