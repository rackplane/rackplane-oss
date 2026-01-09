# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Print Job Schemas
Pydantic models for print job API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from app.models.print_job import PrintJobStatus, PrintJobType


class PrintJobResponse(BaseModel):
    """Print job response schema"""
    id: int
    job_id: Optional[str] = None  # Alias for id (MUST be STRING for client compatibility)
    job_type: PrintJobType
    status: PrintJobStatus
    asset_id: Optional[int] = None
    container_id: Optional[int] = None
    rack_id: Optional[int] = None
    label_size: str
    printer_ip: Optional[str] = None
    instance: int
    total_instances: int
    label_data: Optional[Dict[str, Any]] = None
    label_image_url: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    error: Optional[str] = None  # Alias for error_message (client compatibility)
    printer_response: Optional[Dict[str, Any]] = None
    created_by_user_id: Optional[int] = None
    priority: int
    retry_count: int
    max_retries: int
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    # Client-required fields (populated from related asset/container)
    asset_tag: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    qr_data: Optional[str] = None  # JSON string with id
    hostname: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm_with_relations(cls, job, asset=None, container=None):
        """Create response with related asset/container data populated"""
        data = {
            "id": job.id,
            "job_id": str(job.id),  # MUST be a STRING for client compatibility
            "job_type": job.job_type,
            "status": job.status,
            "asset_id": job.asset_id,
            "container_id": job.container_id,
            "rack_id": job.rack_id,
            "label_size": job.label_size or "24mm",  # Default to 24mm if not set
            "printer_ip": job.printer_ip or "",  # Default to empty string if not set (client will use default)
            "instance": job.instance,
            "total_instances": job.total_instances,
            "label_data": job.label_data,
            "label_image_url": job.label_image_url,
            "assigned_agent_id": job.assigned_agent_id,
            "assigned_at": job.assigned_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "success": job.success,
            "error_message": job.error_message,
            "error": job.error_message,  # Alias for client compatibility
            "printer_response": job.printer_response,
            "created_by_user_id": job.created_by_user_id,
            "priority": job.priority,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "notes": job.notes,
            "custom_fields": job.custom_fields or {},
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
        
        # Populate from asset if available
        if asset:
            data["asset_tag"] = asset.asset_tag
            data["manufacturer"] = asset.manufacturer
            data["model"] = asset.model
            data["serial_number"] = asset.serial_number
            data["hostname"] = asset.hostname
            data["qr_data"] = json.dumps({"id": asset.id})
        
        # Populate from container if available
        elif container:
            data["asset_tag"] = container.name or f"CONTAINER-{container.id}"
            data["manufacturer"] = None
            data["model"] = container.container_type
            data["serial_number"] = container.barcode or f"CNT-{container.id}"
            data["hostname"] = None
            data["qr_data"] = json.dumps({"id": container.id})
        
        return cls(**data)


class PrintJobListResponse(BaseModel):
    """List of print jobs with pagination"""
    total: int
    count: int  # Alias for total (for client compatibility) - should equal total
    limit: int
    offset: int
    jobs: List[PrintJobResponse]


class PrintJobCreate(BaseModel):
    """Request to create a new print job"""
    job_type: PrintJobType
    asset_id: Optional[int] = None
    container_id: Optional[int] = None
    rack_id: Optional[int] = None
    label_size: str = Field("24mm", description="Label size: 12mm, 24mm, or 36mm")
    printer_ip: Optional[str] = None
    instance: int = Field(1, ge=1, description="Instance number for bulk printing")
    total_instances: int = Field(1, ge=1, description="Total instances in batch")
    priority: int = Field(0, description="Job priority (higher = more priority)")
    label_data: Optional[Dict[str, Any]] = None
    label_image_url: Optional[str] = None
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class CompletePrintJobRequest(BaseModel):
    """Request to complete a print job"""
    success: bool
    error_message: Optional[str] = None
    printer_response: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class AgentHeartbeatRequest(BaseModel):
    """Agent heartbeat request"""
    agent_id: str
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    operating_system: Optional[str] = None
    supported_label_sizes: Optional[List[str]] = None
    printer_ips: Optional[List[str]] = None
    max_concurrent_jobs: Optional[int] = None
    current_job_count: Optional[int] = None  # How many jobs currently running


class AgentHeartbeatResponse(BaseModel):
    """Agent heartbeat response"""
    status: str = "ok"
    message: Optional[str] = None
    agent_id: str
    last_heartbeat: datetime


class AgentLoginRequest(BaseModel):
    """Agent authentication request"""
    agent_id: str
    agent_secret: str  # Required for authentication
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None


class AgentLoginResponse(BaseModel):
    """Agent authentication response"""
    access_token: str
    token_type: str = "bearer"
    agent_id: str
    expires_in: Optional[int] = None

