# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Reports API Endpoints
Compliance, utilization, and analytics reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from io import BytesIO

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/asset-utilization")
async def get_asset_utilization_report(
    datacenter_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate asset utilization report"""
    service = ReportService(db)
    return service.asset_utilization_report(datacenter_id, asset_type)


@router.get("/capacity-summary")
async def get_capacity_summary(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate capacity summary report (space, power, cooling)"""
    # Ensure tenant context is set from user
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.capacity_summary(datacenter_id)


@router.get("/inventory-value")
async def get_inventory_value_report(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate inventory value and depreciation report"""
    # Ensure tenant context is set from user
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.inventory_value_report(datacenter_id)


@router.get("/pue")
async def get_pue_report(
    datacenter_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate Power Usage Effectiveness (PUE) report"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.pue_report(datacenter_id, days)


@router.get("/lifecycle-status")
async def get_lifecycle_status_report(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate asset lifecycle status report"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.lifecycle_status_report(datacenter_id)


@router.get("/maintenance-summary")
async def get_maintenance_summary(
    days: int = Query(30, ge=1, le=365),
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate maintenance summary report"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.maintenance_summary_report(days, datacenter_id)


@router.get("/environmental-compliance")
async def get_environmental_compliance_report(
    datacenter_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate environmental compliance report (temperature, humidity)"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.environmental_compliance_report(datacenter_id, days)


@router.get("/audit-trail")
async def get_audit_trail(
    asset_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate audit trail report"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.audit_trail_report(asset_id, days)


@router.get("/export/inventory")
async def export_inventory(
    format: str = Query("xlsx", regex="^(xlsx|csv|pdf|ptouch-csv)$"),
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export complete inventory to file"""
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)

    if format == "xlsx":
        file_content, filename = service.export_inventory_xlsx(datacenter_id)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "csv":
        file_content, filename = service.export_inventory_csv(datacenter_id)
        media_type = "text/csv"
    elif format == "pdf":
        file_content, filename = service.export_inventory_pdf(datacenter_id)
        media_type = "application/pdf"
    elif format == "ptouch-csv":
        file_content, filename = service.export_ptouch_csv(datacenter_id)
        media_type = "text/csv"

    return Response(
        content=file_content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard summary statistics"""
    # Ensure tenant context is set from user
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    if not get_current_tenant_id() and current_user.tenant_id:
        set_current_tenant_id(current_user.tenant_id)
    
    service = ReportService(db)
    return service.dashboard_summary(datacenter_id)


@router.get("/admin/dashboard")
async def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get system-wide admin dashboard summary (super admin only)"""
    from app.models.user_role import UserRole
    
    # Check if user is super admin
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    
    service = ReportService(db)
    return service.admin_dashboard_summary()


@router.get("/financial/depreciation")
async def get_depreciation_schedule(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate depreciation schedule report"""
    service = ReportService(db)
    return service.depreciation_schedule(datacenter_id)
