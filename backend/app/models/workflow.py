# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Workflow Automation Models
MACs (Moves, Adds, Changes) and SOP automation
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class WorkflowType(str, enum.Enum):
    """Workflow types"""
    DEPLOYMENT = "deployment"
    DECOMMISSION = "decommission"
    MOVE = "move"
    UPGRADE = "upgrade"
    CABLE_ROUTING = "cable_routing"
    AUDIT = "audit"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, enum.Enum):
    """Individual step status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Workflow(Base, TenantMixin):
    """Workflow template definitions"""
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)

    # Workflow Definition
    name = Column(String(300), nullable=False, index=True)
    workflow_type = Column(SQLEnum(WorkflowType), nullable=False)
    description = Column(Text)

    # Configuration
    is_template = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Steps (ordered list of steps)
    steps_definition = Column(JSON, default=[])  # Array of step definitions

    # Automation
    automated = Column(Boolean, default=False)
    auto_progress = Column(Boolean, default=False)  # Auto-advance steps

    # Approval Requirements
    requires_approval = Column(Boolean, default=False)
    approvers = Column(JSON, default=[])

    # Metadata
    created_by = Column(String(200))
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workflow {self.name}>"


class WorkflowExecution(Base, TenantMixin):
    """Workflow execution instances"""
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    # Execution Details
    execution_name = Column(String(300), nullable=False)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)

    # Asset/Target
    target_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    target_description = Column(Text)

    # Scheduling
    scheduled_start = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Duration
    estimated_duration_hours = Column(Float)
    actual_duration_hours = Column(Float)

    # Personnel
    assigned_to = Column(String(200))
    executed_by = Column(String(200))

    # Progress
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    current_step = Column(Integer, default=0)

    # Results
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_log = Column(JSON, default=[])

    # Approval
    approval_status = Column(String(50), nullable=True)
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    steps = relationship("WorkflowStep", back_populates="execution", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowExecution {self.execution_name} - {self.status}>"


class WorkflowStep(Base, TenantMixin):
    """Individual steps within workflow execution"""
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id"), nullable=False)

    # Step Details
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(300), nullable=False)
    description = Column(Text)

    # Status
    status = Column(SQLEnum(StepStatus), default=StepStatus.PENDING)

    # Execution
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)

    # Assignment
    assigned_to = Column(String(200))
    completed_by = Column(String(200))

    # Requirements
    requires_confirmation = Column(Boolean, default=False)
    confirmed = Column(Boolean, default=False)
    confirmed_by = Column(String(200), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # Instructions
    instructions = Column(Text)
    checklist = Column(JSON, default=[])

    # Results
    result = Column(Text, nullable=True)
    output_data = Column(JSON, default={})

    # Documentation
    photos = Column(JSON, default=[])
    attachments = Column(JSON, default=[])

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="steps")

    def __repr__(self):
        return f"<WorkflowStep {self.step_number}: {self.step_name}>"
