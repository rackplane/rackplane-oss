# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Workflow Service - Business Logic
Workflow automation for MACs and SOPs
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from app.models.workflow import Workflow, WorkflowExecution, WorkflowStep, WorkflowStatus, StepStatus
from app.schemas.workflow import WorkflowCreate, WorkflowExecutionCreate, StepUpdate


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(self, workflow_data: WorkflowCreate) -> Workflow:
        """Create workflow template"""
        workflow = Workflow(**workflow_data.model_dump())
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def start_execution(self, execution_data: WorkflowExecutionCreate) -> WorkflowExecution:
        """Start workflow execution from template"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Workflow).filter(Workflow.id == execution_data.workflow_id)
        query = apply_tenant_filter(query, Workflow)
        workflow = query.first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow template not found")

        # Create execution
        execution = WorkflowExecution(
            **execution_data.model_dump(),
            status=WorkflowStatus.PENDING,
            total_steps=len(workflow.steps_definition)
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # Create steps from template
        for idx, step_def in enumerate(workflow.steps_definition, 1):
            step = WorkflowStep(
                execution_id=execution.id,
                step_number=idx,
                step_name=step_def.get("name", f"Step {idx}"),
                description=step_def.get("description"),
                instructions=step_def.get("instructions"),
                requires_confirmation=step_def.get("requires_confirmation", False),
                status=StepStatus.PENDING
            )
            self.db.add(step)

        self.db.commit()
        return execution

    def advance_step(self, execution_id: int) -> WorkflowExecution:
        """Advance workflow to next step"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id)
        query = apply_tenant_filter(query, WorkflowExecution)
        execution = query.first()
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow execution not found")

        execution.current_step += 1
        execution.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update_step(self, step_id: int, step_update: StepUpdate) -> WorkflowStep:
        """Update workflow step"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id)
        query = apply_tenant_filter(query, WorkflowStep)
        step = query.first()
        if not step:
            raise HTTPException(status_code=404, detail="Step not found")

        for key, value in step_update.model_dump(exclude_unset=True).items():
            setattr(step, key, value)

        step.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(step)
        return step

    def create_deployment_workflow(self, asset_id: int, rack_id: int, u_position: int) -> WorkflowExecution:
        """Create standard deployment workflow"""
        # This would use a predefined deployment workflow template
        # Simplified implementation
        from app.models.workflow import WorkflowType

        execution = WorkflowExecution(
            workflow_id=1,  # Assume ID 1 is deployment template
            execution_name=f"Deploy Asset {asset_id}",
            target_asset_id=asset_id,
            status=WorkflowStatus.PENDING
        )
        self.db.add(execution)
        self.db.commit()
        return execution

    def create_decommission_workflow(self, asset_id: int) -> WorkflowExecution:
        """Create standard decommission workflow"""
        from app.core.tenant_query import apply_tenant_filter
        from app.models.asset import Asset
        
        # Verify asset exists (tenant-scoped)
        query = self.db.query(Asset).filter(Asset.id == asset_id)
        query = apply_tenant_filter(query, Asset)
        asset = query.first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        execution = WorkflowExecution(
            workflow_id=2,  # Assume ID 2 is decommission template
            execution_name=f"Decommission Asset {asset_id}",
            target_asset_id=asset_id,
            status=WorkflowStatus.PENDING
        )
        self.db.add(execution)
        self.db.commit()
        return execution

    def create_move_workflow(self, asset_id: int, target_rack_id: int, target_u_position: int) -> WorkflowExecution:
        """Create standard move workflow"""
        execution = WorkflowExecution(
            workflow_id=3,  # Assume ID 3 is move template
            execution_name=f"Move Asset {asset_id}",
            target_asset_id=asset_id,
            status=WorkflowStatus.PENDING
        )
        self.db.add(execution)
        self.db.commit()
        return execution
