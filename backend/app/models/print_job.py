# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Print Job Model
Queue system for distributed label printing via print agents
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class PrintJobStatus(str, enum.Enum):
    """Print job status"""
    PENDING = "pending"
    ASSIGNED = "assigned"  # Assigned to an agent
    PRINTING = "printing"  # Currently being printed
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrintJobType(str, enum.Enum):
    """Type of print job"""
    ASSET_LABEL = "asset_label"
    CONTAINER_LABEL = "container_label"
    RACK_LABEL = "rack_label"


class PrintJob(Base, TenantMixin):
    """Print job queue for distributed printing"""
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Job Details
    job_type = Column(SQLEnum(PrintJobType), nullable=False)
    status = Column(SQLEnum(PrintJobStatus), default=PrintJobStatus.PENDING, nullable=False, index=True)
    
    # Target (what to print)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    
    # Print Configuration
    label_size = Column(String(20), default="24mm", nullable=False)  # 12mm, 24mm, 36mm
    printer_ip = Column(String(50), nullable=True)  # Optional: specific printer IP
    instance = Column(Integer, default=1)  # For bulk printing
    total_instances = Column(Integer, default=1)  # Total in batch
    
    # Job Data (serialized label data)
    label_data = Column(JSON, nullable=True)  # Serialized label image/data
    label_image_url = Column(String(500), nullable=True)  # URL to generated label image
    
    # Assignment
    assigned_agent_id = Column(String(100), nullable=True, index=True)  # Agent identifier
    assigned_at = Column(DateTime, nullable=True)
    
    # Execution
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    printer_response = Column(JSON, nullable=True)  # Response from printer
    
    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    priority = Column(Integer, default=0)  # Higher = more priority
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    asset = relationship("Asset", foreign_keys=[asset_id])
    container = relationship("StorageContainer", foreign_keys=[container_id])
    rack = relationship("Rack", foreign_keys=[rack_id])
    
    def __repr__(self):
        return f"<PrintJob(id={self.id}, type={self.job_type}, status={self.status})>"


class PrintAgent(Base, TenantMixin):
    """Print agent registration and status"""
    __tablename__ = "print_agents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Agent Identification
    agent_id = Column(String(100), unique=True, nullable=False, index=True)  # Unique agent identifier
    agent_name = Column(String(200), nullable=True)  # Human-readable name
    agent_version = Column(String(50), nullable=True)  # Agent software version
    secret_hash = Column(String(255), nullable=True)  # Bcrypt hash of agent secret for authentication
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime, nullable=True, index=True)
    heartbeat_interval_seconds = Column(Integer, default=30)  # Expected heartbeat interval
    
    # Capabilities
    supported_label_sizes = Column(JSON, default=["12mm", "24mm"])  # List of supported sizes
    printer_ips = Column(JSON, default=[])  # List of printer IPs this agent can access
    max_concurrent_jobs = Column(Integer, default=1)  # How many jobs can run simultaneously
    
    # Statistics
    total_jobs_completed = Column(Integer, default=0)
    total_jobs_failed = Column(Integer, default=0)
    last_job_at = Column(DateTime, nullable=True)
    
    # Metadata
    hostname = Column(String(200), nullable=True)
    ip_address = Column(String(50), nullable=True)
    operating_system = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<PrintAgent(id={self.id}, agent_id={self.agent_id}, active={self.is_active})>"

