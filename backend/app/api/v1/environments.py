# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
DEV Troubleshooting API
Manages development/testing environment troubleshooting operations including device management and power cycling
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import subprocess
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.asset import Asset
from app.models.user import User
from app.models.environment import Environment as EnvironmentModel

logger = logging.getLogger(__name__)

router = APIRouter()


class EnvironmentBase(BaseModel):
    """Base environment model"""
    id: int
    name: str
    ssh_link: str
    ipmi_link: str
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None


class EnvironmentUpdate(BaseModel):
    """Model for updating environment links"""
    ssh_link: Optional[str] = None
    ipmi_link: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None


class EnvironmentDevice(BaseModel):
    """Device in an environment"""
    id: int
    hostname: str
    asset_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: str
    has_console: bool = False
    has_ipmi: bool = False
    console_link: Optional[str] = None
    ipmi_link: Optional[str] = None
    console_username: Optional[str] = None
    console_password: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None


class PingResult(BaseModel):
    """Result of ping operation"""
    success: bool
    output: str
    error: Optional[str] = None


@router.get("/", response_model=List[EnvironmentBase])
async def list_environments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all environments for the current tenant.
    
    Note: Passwords are returned in plain text for internal debugging use only.
    These should never be used for production/external systems.
    """
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel)
    query = apply_tenant_filter(query, EnvironmentModel)
    envs = query.all()

    return [
        EnvironmentBase(
            id=env.id,
            name=env.name,
            ssh_link=env.ssh_link,
            ipmi_link=env.ipmi_link,
            ssh_username=env.ssh_username,
            ssh_password=env.ssh_password,
            ipmi_username=env.ipmi_username,
            ipmi_password=env.ipmi_password,
        )
        for env in envs
    ]


class EnvironmentCreate(BaseModel):
    """Model for creating a new environment"""
    name: str
    ssh_link: str
    ipmi_link: str
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None


@router.post("/", response_model=EnvironmentBase, status_code=status.HTTP_201_CREATED)
async def create_environment(
    env_data: EnvironmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new environment for the current tenant.
    
    Note: Passwords are stored in plain text for internal debugging use only.
    These should never be used for production/external systems.
    """
    from app.core.tenant import get_current_tenant_id
    
    tenant_id = get_current_tenant_id()
    
    # Create new environment
    new_env = EnvironmentModel(
        name=env_data.name,
        ssh_link=env_data.ssh_link,
        ipmi_link=env_data.ipmi_link,
        ssh_username=env_data.ssh_username,
        ssh_password=env_data.ssh_password,
        ipmi_username=env_data.ipmi_username,
        ipmi_password=env_data.ipmi_password,
        tenant_id=tenant_id
    )
    
    db.add(new_env)
    db.commit()
    db.refresh(new_env)
    
    return EnvironmentBase(
        id=new_env.id,
        name=new_env.name,
        ssh_link=new_env.ssh_link,
        ipmi_link=new_env.ipmi_link,
        ssh_username=new_env.ssh_username,
        ssh_password=new_env.ssh_password,
        ipmi_username=new_env.ipmi_username,
        ipmi_password=new_env.ipmi_password,
    )


@router.get("/{env_id}", response_model=EnvironmentBase)
async def get_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get details for a specific environment"""
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    return EnvironmentBase(
        id=env.id,
        name=env.name,
        ssh_link=env.ssh_link,
        ipmi_link=env.ipmi_link,
        ssh_username=env.ssh_username,
        ssh_password=env.ssh_password,
        ipmi_username=env.ipmi_username,
        ipmi_password=env.ipmi_password,
    )


@router.put("/{env_id}", response_model=EnvironmentBase)
async def update_environment(
    env_id: int,
    update: EnvironmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update environment links and credentials.
    
    Note: Passwords are stored in plain text for internal debugging use only.
    These should never be used for production/external systems.
    """
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    if update.ssh_link is not None:
        env.ssh_link = update.ssh_link
    if update.ipmi_link is not None:
        env.ipmi_link = update.ipmi_link
    if update.ssh_username is not None:
        env.ssh_username = update.ssh_username
    if update.ssh_password is not None:
        env.ssh_password = update.ssh_password
    if update.ipmi_username is not None:
        env.ipmi_username = update.ipmi_username
    if update.ipmi_password is not None:
        env.ipmi_password = update.ipmi_password

    db.commit()
    db.refresh(env)

    return EnvironmentBase(
        id=env.id,
        name=env.name,
        ssh_link=env.ssh_link,
        ipmi_link=env.ipmi_link,
        ssh_username=env.ssh_username,
        ssh_password=env.ssh_password,
        ipmi_username=env.ipmi_username,
        ipmi_password=env.ipmi_password,
    )


@router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an environment"""
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    db.delete(env)
    db.commit()


@router.get("/{env_id}/devices", response_model=List[EnvironmentDevice])
async def get_environment_devices(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all devices belonging to an environment"""
    from app.core.tenant_query import apply_tenant_filter

    # Ensure environment exists and belongs to current tenant
    env_query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    env_query = apply_tenant_filter(env_query, EnvironmentModel)
    env = env_query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    # Query assets where hostname starts with environment name followed by /
    query = db.query(Asset).filter(
        Asset.hostname.like(f"{env.name}/%")
    )
    query = apply_tenant_filter(query, Asset)
    devices = query.all()

    return [
        EnvironmentDevice(
            id=device.id,
            hostname=device.hostname or "",
            asset_type=device.asset_type,
            manufacturer=device.manufacturer,
            model=device.model,
            status=device.status.value if device.status else "unknown",
            has_console=device.has_console or False,
            has_ipmi=device.has_ipmi or False,
            console_link=device.console_link,
            ipmi_link=device.ipmi_link,
            console_username=device.console_username,
            console_password=device.console_password,
            ipmi_username=device.ipmi_username,
            ipmi_password=device.ipmi_password,
        )
        for device in devices
    ]


@router.post("/{env_id}/ping", response_model=PingResult)
async def ping_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Ping the environment server"""
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    ssh_link = env.ssh_link

    try:
        result = subprocess.run(
            ["ping", "-c", "4", ssh_link],
            capture_output=True,
            text=True,
            timeout=10
        )

        return PingResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return PingResult(
            success=False,
            output="",
            error="Ping request timed out"
        )
    except Exception as e:
        logger.error(f"Error pinging {ssh_link}: {e}")
        return PingResult(
            success=False,
            output="",
            error=str(e)
        )


@router.post("/{env_id}/ping-ipmi", response_model=PingResult)
async def ping_ipmi(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Ping the environment IPMI"""
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    # Extract hostname from IPMI link (remove https://)
    ipmi_link = env.ipmi_link.replace("https://", "").replace("http://", "")

    try:
        result = subprocess.run(
            ["ping", "-c", "4", ipmi_link],
            capture_output=True,
            text=True,
            timeout=10
        )

        return PingResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return PingResult(
            success=False,
            output="",
            error="Ping request timed out"
        )
    except Exception as e:
        logger.error(f"Error pinging IPMI {ipmi_link}: {e}")
        return PingResult(
            success=False,
            output="",
            error=str(e)
        )


@router.post("/{env_id}/power-cycle")
async def power_cycle_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Power cycle the environment server (placeholder - implement with IPMI/BMC commands)"""
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(EnvironmentModel).filter(EnvironmentModel.id == env_id)
    query = apply_tenant_filter(query, EnvironmentModel)
    env = query.first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {env_id} not found"
        )

    # This is a placeholder - actual implementation would require IPMI credentials
    # and use ipmitool or similar to power cycle the server
    logger.warning(f"Power cycle requested for environment {env.name} (ID: {env_id}) - not implemented yet")

    return {
        "success": False,
        "message": "Power cycle functionality requires IPMI credentials and ipmitool configuration",
        "environment_id": env_id,
        "environment_name": env.name,
    }


@router.post("/devices/{device_id}/power-cycle")
async def power_cycle_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Power cycle a specific device (placeholder - implement with IPMI/PDU commands)"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.id == device_id)
    query = apply_tenant_filter(query, Asset)
    device = query.first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # This is a placeholder - actual implementation would require IPMI/PDU credentials
    logger.warning(f"Power cycle requested for device {device.hostname} (ID: {device_id}) - not implemented yet")

    return {
        "success": False,
        "message": "Power cycle functionality requires IPMI/PDU credentials and configuration",
        "device_id": device_id,
        "hostname": device.hostname
    }
