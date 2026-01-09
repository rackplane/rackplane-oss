# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Maintenance API Endpoints
Maintenance records and predictive analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.maintenance import MaintenanceRecord, MaintenancePrediction, MaintenanceStatus, MaintenanceType
from app.models.user import User
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate, PredictionResponse
from app.services.maintenance_service import MaintenanceService

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_maintenance_record(
    maintenance: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new maintenance record"""
    service = MaintenanceService(db)
    return service.create_maintenance(maintenance)


@router.get("/")
async def list_maintenance_records(
    asset_id: Optional[int] = None,
    status: Optional[MaintenanceStatus] = None,
    maintenance_type: Optional[MaintenanceType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List maintenance records with filters for the current tenant"""
    from sqlalchemy.orm import joinedload
    from app.core.tenant_query import apply_tenant_filter

    query = db.query(MaintenanceRecord).options(joinedload(MaintenanceRecord.asset))
    query = apply_tenant_filter(query, MaintenanceRecord)

    if asset_id:
        query = query.filter(MaintenanceRecord.asset_id == asset_id)
    if status:
        query = query.filter(MaintenanceRecord.status == status)
    if maintenance_type:
        query = query.filter(MaintenanceRecord.maintenance_type == maintenance_type)

    total = query.count()
    records = query.order_by(MaintenanceRecord.scheduled_date.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "records": records
    }


@router.get("/{maintenance_id}")
async def get_maintenance_record(
    maintenance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get maintenance record details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id)
    query = apply_tenant_filter(query, MaintenanceRecord)
    record = query.first()
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    return record


@router.put("/{maintenance_id}")
async def update_maintenance_record(
    maintenance_id: int,
    maintenance_update: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update maintenance record"""
    service = MaintenanceService(db)
    return service.update_maintenance(maintenance_id, maintenance_update)


@router.post("/{maintenance_id}/start")
async def start_maintenance(
    maintenance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark maintenance as started"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id)
    query = apply_tenant_filter(query, MaintenanceRecord)
    record = query.first()
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    record.status = MaintenanceStatus.IN_PROGRESS
    record.started_at = datetime.utcnow()
    db.commit()
    db.refresh(record)

    return record


@router.post("/{maintenance_id}/complete")
async def complete_maintenance(
    maintenance_id: int,
    work_performed: Optional[str] = None,
    issue_resolved: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark maintenance as completed"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id)
    query = apply_tenant_filter(query, MaintenanceRecord)
    record = query.first()
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    record.status = MaintenanceStatus.COMPLETED
    record.completed_at = datetime.utcnow()
    record.issue_resolved = issue_resolved

    if work_performed:
        record.work_performed = work_performed

    if record.started_at:
        duration = (record.completed_at - record.started_at).total_seconds() / 3600
        record.actual_duration_hours = duration

    # Calculate MTTR if failure was detected
    if record.failure_detected_at:
        mttr = (record.completed_at - record.failure_detected_at).total_seconds() / 60
        record.mttr_minutes = mttr

    db.commit()
    db.refresh(record)

    return record


@router.get("/asset/{asset_id}/history")
async def get_asset_maintenance_history(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get complete maintenance history for an asset"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.asset_id == asset_id
    )
    query = apply_tenant_filter(query, MaintenanceRecord)
    records = query.order_by(MaintenanceRecord.scheduled_date.desc()).all()

    return records


@router.get("/predictions/", response_model=List[PredictionResponse])
async def get_maintenance_predictions(
    asset_id: Optional[int] = None,
    days_ahead: int = Query(30, ge=1, le=365),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get predictive maintenance predictions"""
    from sqlalchemy.orm import joinedload
    from app.core.tenant_query import apply_tenant_filter

    cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

    query = db.query(MaintenancePrediction).options(joinedload(MaintenancePrediction.asset)).filter(
        MaintenancePrediction.confidence_score >= min_confidence,
        MaintenancePrediction.predicted_failure_date.isnot(None),
        MaintenancePrediction.predicted_failure_date <= cutoff_date
    )
    query = apply_tenant_filter(query, MaintenancePrediction)

    if asset_id:
        query = query.filter(MaintenancePrediction.asset_id == asset_id)

    predictions = query.order_by(MaintenancePrediction.predicted_failure_date).all()

    return predictions


@router.post("/predictions/generate")
async def generate_predictions(
    asset_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger predictive maintenance analysis"""
    service = MaintenanceService(db)
    return service.generate_predictions(asset_id)


@router.get("/analytics/mttr")
async def get_mttr_analytics(
    asset_type: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get Mean Time To Repair analytics"""
    service = MaintenanceService(db)
    return service.get_mttr_analytics(asset_type, days)
