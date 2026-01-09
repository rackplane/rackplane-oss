# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Connection Pydantic Schemas - Phase 2: Port-based connections"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.connections import ConnectionEnd


class ConnectionCreate(BaseModel):
    """Schema for creating a connection"""
    cable_id: int = Field(..., description="ID of the cable asset")
    # Phase 2: Use port_id (preferred) or device_id + port_label (deprecated)
    port_id: Optional[int] = Field(None, description="ID of the network port being connected (Phase 2)")
    device_id: Optional[int] = Field(None, description="DEPRECATED: ID of the device asset being connected")
    port_label: Optional[str] = Field(None, max_length=100, description="DEPRECATED: Port label on the device")
    
    @model_validator(mode='after')
    def validate_connection_target(self):
        if self.port_id is None and self.device_id is None:
            raise ValueError("Either port_id or device_id must be provided")
        return self


class ConnectionResponse(BaseModel):
    """Schema for connection response"""
    id: int
    cable_asset_id: int
    # Phase 2: Include both for backward compatibility
    port_id: Optional[int] = None  # New port-based connection
    device_asset_id: Optional[int] = None  # Deprecated but included for compat
    port_label: Optional[str] = None  # Deprecated
    end_label: str  # 'A' or 'B'
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConnectRequest(BaseModel):
    """Schema for smart connect endpoint - Phase 2: Port-based"""
    cable_id: int = Field(..., description="ID of the cable asset")
    # Phase 2: Use port_id (preferred)
    port_id: Optional[int] = Field(None, description="ID of the network port being connected")
    # Deprecated but kept for backward compatibility
    device_id: Optional[int] = Field(None, description="DEPRECATED: ID of the device asset")
    port_label: Optional[str] = Field(None, max_length=100, description="DEPRECATED: Port label on the device")
    
    @model_validator(mode='after')
    def validate_connection_target(self):
        if self.port_id is None and self.device_id is None:
            raise ValueError("Either port_id or device_id must be provided")
        return self


class ConnectResponse(BaseModel):
    """Schema for smart connect response"""
    connection: ConnectionResponse
    end_label: str = Field(..., description="Which end was assigned ('A' or 'B')")
    message: str = Field(..., description="Human-readable message about the connection")
    # Phase 3: Compatibility validation result
    compatibility: Optional[Dict[str, Any]] = Field(
        None,
        description="Cable/port compatibility result: {compatible, level, message, allow_connection}"
    )


class CircuitEndpoint(BaseModel):
    """Schema for one end of a circuit"""
    device_id: int
    device_name: str
    device_type: str
    device_model: str = ""
    port_id: Optional[int] = None
    port_number: Optional[str] = None
    port_name: Optional[str] = None
    port_type: Optional[str] = None
    rack_name: Optional[str] = None
    rack_code: Optional[str] = None
    # Deprecated fields for backward compatibility
    port: Optional[str] = None  # Old port_label field


class Circuit(BaseModel):
    """Schema for circuit view (cable with both ends)"""
    cable: dict
    end_a: Optional[CircuitEndpoint] = None
    end_b: Optional[CircuitEndpoint] = None

