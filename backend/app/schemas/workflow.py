# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Workflow Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.workflow import WorkflowType, WorkflowStatus, StepStatus


class WorkflowCreate(BaseModel):
    name: str
    workflow_type: WorkflowType
    description: Optional[str] = None
    steps_definition: List[dict] = []
    automated: bool = False


class WorkflowExecutionCreate(BaseModel):
    workflow_id: int
    execution_name: str
    target_asset_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    assigned_to: Optional[str] = None


class StepUpdate(BaseModel):
    status: Optional[StepStatus] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    confirmed: Optional[bool] = None
