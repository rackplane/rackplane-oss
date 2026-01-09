# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Environmental Monitoring API Endpoints
Temperature, humidity, and environmental sensor management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.environmental import EnvironmentalSensor, EnvironmentalReading
from app.models.user import User
from app.schemas.environmental import SensorCreate, ReadingCreate, SensorResponse
from app.services.environmental_service import EnvironmentalService

router = APIRouter()


# ===== SENSOR MANAGEMENT =====

@router.post("/sensors", status_code=status.HTTP_201_CREATED)
async def create_sensor(
    sensor: SensorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Register a new environmental sensor"""
    service = EnvironmentalService(db)
    try:
        return service.create_sensor(sensor)
    except IntegrityError as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
             raise HTTPException(status_code=400, detail="Sensor with this ID already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sensors")
async def list_sensors(
    datacenter_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List environmental sensors for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(EnvironmentalSensor)
    query = apply_tenant_filter(query, EnvironmentalSensor)

    if datacenter_id:
        query = query.filter(EnvironmentalSensor.datacenter_id == datacenter_id)
    if sensor_type:
        query = query.filter(EnvironmentalSensor.sensor_type == sensor_type)
    if is_active is not None:
        query = query.filter(EnvironmentalSensor.is_active == is_active)

    sensors = query.all()
    return sensors


@router.get("/sensors/{sensor_id}")
async def get_sensor(
    sensor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get sensor details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(EnvironmentalSensor).filter(EnvironmentalSensor.id == sensor_id)
    query = apply_tenant_filter(query, EnvironmentalSensor)
    sensor = query.first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.put("/sensors/{sensor_id}")
async def update_sensor(
    sensor_id: int,
    sensor_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update sensor configuration"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(EnvironmentalSensor).filter(EnvironmentalSensor.id == sensor_id)
    query = apply_tenant_filter(query, EnvironmentalSensor)
    sensor = query.first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    for key, value in sensor_update.items():
        if hasattr(sensor, key):
            setattr(sensor, key, value)

    sensor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sensor)

    return sensor


# ===== SENSOR READINGS =====

@router.post("/readings", status_code=status.HTTP_201_CREATED)
async def record_reading(
    reading: ReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record a new sensor reading"""
    service = EnvironmentalService(db)
    return service.record_reading(reading)


@router.post("/readings/batch", status_code=status.HTTP_201_CREATED)
async def record_batch_readings(
    readings: list[ReadingCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record multiple sensor readings at once"""
    service = EnvironmentalService(db)
    return service.record_batch_readings(readings)


@router.get("/readings")
async def get_readings(
    sensor_id: Optional[int] = None,
    datacenter_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get sensor readings for specified time period"""
    from app.core.tenant_query import apply_tenant_filter
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(EnvironmentalReading).filter(
        EnvironmentalReading.timestamp >= cutoff_time
    )
    query = apply_tenant_filter(query, EnvironmentalReading)

    if sensor_id:
        query = query.filter(EnvironmentalReading.sensor_id == sensor_id)
    elif datacenter_id:
        # Join with sensor to filter by datacenter
        query = query.join(EnvironmentalSensor).filter(
            EnvironmentalSensor.datacenter_id == datacenter_id
        )

    readings = query.order_by(EnvironmentalReading.timestamp.desc()).all()
    return readings


@router.get("/readings/latest")
async def get_latest_readings(
    datacenter_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get latest reading from each sensor"""
    service = EnvironmentalService(db)
    return service.get_latest_readings(datacenter_id, sensor_type)


@router.get("/readings/anomalies")
async def get_anomalies(
    datacenter_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get anomalous sensor readings"""
    from app.core.tenant_query import apply_tenant_filter
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(EnvironmentalReading).filter(
        EnvironmentalReading.timestamp >= cutoff_time,
        EnvironmentalReading.is_anomaly == True
    )
    query = apply_tenant_filter(query, EnvironmentalReading)

    if datacenter_id:
        query = query.join(EnvironmentalSensor).filter(
            EnvironmentalSensor.datacenter_id == datacenter_id
        )

    anomalies = query.order_by(EnvironmentalReading.timestamp.desc()).all()
    return anomalies


@router.get("/readings/threshold-breaches")
async def get_threshold_breaches(
    datacenter_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get readings that breached thresholds"""
    from app.core.tenant_query import apply_tenant_filter
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(EnvironmentalReading).filter(
        EnvironmentalReading.timestamp >= cutoff_time,
        EnvironmentalReading.threshold_breached.isnot(None)
    )
    query = apply_tenant_filter(query, EnvironmentalReading)

    if datacenter_id:
        query = query.join(EnvironmentalSensor).filter(
            EnvironmentalSensor.datacenter_id == datacenter_id
        )

    breaches = query.order_by(EnvironmentalReading.timestamp.desc()).all()
    return breaches


# ===== ANALYTICS =====

@router.get("/analytics/temperature-trends")
async def get_temperature_trends(
    datacenter_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get temperature trends over time"""
    service = EnvironmentalService(db)
    return service.get_temperature_trends(datacenter_id, days)


@router.get("/analytics/humidity-trends")
async def get_humidity_trends(
    datacenter_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get humidity trends over time"""
    service = EnvironmentalService(db)
    return service.get_humidity_trends(datacenter_id, days)


@router.get("/analytics/correlation")
async def get_environmental_asset_correlation(
    asset_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Correlate environmental conditions with asset location"""
    service = EnvironmentalService(db)
    return service.get_asset_correlation(asset_id, hours)


@router.get("/alerts/active")
async def get_active_environmental_alerts(
    datacenter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get active environmental alerts"""
    service = EnvironmentalService(db)
    return service.get_active_alerts(datacenter_id)
