# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Workflows API Endpoints
Workflow automation for MACs and SOPs
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.workflow import Workflow, WorkflowExecution, WorkflowStep, WorkflowType, WorkflowStatus
from app.models.user import User
from app.schemas.workflow import WorkflowCreate, WorkflowExecutionCreate, StepUpdate
from app.services.workflow_service import WorkflowService

router = APIRouter()


# ===== WORKFLOW TEMPLATES =====

@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_workflow_template(
    workflow: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new workflow template"""
    service = WorkflowService(db)
    return service.create_workflow(workflow)


@router.get("/templates")
async def list_workflow_templates(
    workflow_type: Optional[WorkflowType] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List workflow templates for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Workflow).filter(Workflow.is_template == True)
    query = apply_tenant_filter(query, Workflow)

    if workflow_type:
        query = query.filter(Workflow.workflow_type == workflow_type)
    if is_active is not None:
        query = query.filter(Workflow.is_active == is_active)

    templates = query.all()
    return templates


@router.get("/templates/{workflow_id}")
async def get_workflow_template(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow template details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Workflow).filter(Workflow.id == workflow_id)
    query = apply_tenant_filter(query, Workflow)
    workflow = query.first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return workflow


# ===== WORKFLOW EXECUTIONS =====

@router.post("/executions", status_code=status.HTTP_201_CREATED)
async def start_workflow_execution(
    execution: WorkflowExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start a new workflow execution from template"""
    service = WorkflowService(db)
    return service.start_execution(execution)


@router.get("/executions")
async def list_workflow_executions(
    status: Optional[WorkflowStatus] = None,
    asset_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List workflow executions for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(WorkflowExecution)
    query = apply_tenant_filter(query, WorkflowExecution)

    if status:
        query = query.filter(WorkflowExecution.status == status)
    if asset_id:
        query = query.filter(WorkflowExecution.target_asset_id == asset_id)

    total = query.count()
    executions = query.order_by(WorkflowExecution.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "executions": executions
    }


@router.get("/executions/{execution_id}")
async def get_workflow_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow execution details with all steps"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id)
    query = apply_tenant_filter(query, WorkflowExecution)
    execution = query.first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    # Include steps (tenant-scoped)
    query = db.query(WorkflowStep).filter(
        WorkflowStep.execution_id == execution_id
    )
    query = apply_tenant_filter(query, WorkflowStep)
    steps = query.order_by(WorkflowStep.step_number).all()

    return {
        "execution": execution,
        "steps": steps
    }


@router.post("/executions/{execution_id}/advance")
async def advance_workflow(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Advance workflow to next step"""
    service = WorkflowService(db)
    return service.advance_step(execution_id)


@router.post("/executions/{execution_id}/complete")
async def complete_workflow(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark workflow execution as completed"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id)
    query = apply_tenant_filter(query, WorkflowExecution)
    execution = query.first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    execution.status = WorkflowStatus.COMPLETED
    execution.completed_at = datetime.utcnow()

    if execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds() / 3600
        execution.actual_duration_hours = duration

    db.commit()
    db.refresh(execution)

    return execution


# ===== WORKFLOW STEPS =====

@router.put("/steps/{step_id}")
async def update_step(
    step_id: int,
    step_update: StepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update workflow step"""
    service = WorkflowService(db)
    return service.update_step(step_id, step_update)


@router.post("/steps/{step_id}/complete")
async def complete_step(
    step_id: int,
    result: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark step as completed"""
    from datetime import datetime
    from app.models.workflow import StepStatus
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(WorkflowStep).filter(WorkflowStep.id == step_id)
    query = apply_tenant_filter(query, WorkflowStep)
    step = query.first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.status = StepStatus.COMPLETED
    step.completed_at = datetime.utcnow()

    if result:
        step.result = result

    if step.started_at:
        duration = (step.completed_at - step.started_at).total_seconds() / 60
        step.duration_minutes = duration

    db.commit()
    db.refresh(step)

    return step


# ===== STANDARD WORKFLOWS =====

@router.post("/standard/deployment")
async def create_deployment_workflow(
    asset_id: int,
    rack_id: int,
    u_position: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create standard deployment workflow"""
    service = WorkflowService(db)
    return service.create_deployment_workflow(asset_id, rack_id, u_position)


@router.post("/standard/decommission")
async def create_decommission_workflow(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create standard decommission workflow"""
    service = WorkflowService(db)
    return service.create_decommission_workflow(asset_id)


@router.post("/standard/move")
async def create_move_workflow(
    asset_id: int,
    target_rack_id: int,
    target_u_position: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create standard move workflow"""
    service = WorkflowService(db)
    return service.create_move_workflow(asset_id, target_rack_id, target_u_position)
