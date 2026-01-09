# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Environmental Service - Business Logic
Environmental monitoring and sensor management
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Optional, List

from app.models.environmental import EnvironmentalSensor, EnvironmentalReading
from app.schemas.environmental import SensorCreate, ReadingCreate
from app.core.config import settings


class EnvironmentalService:
    def __init__(self, db: Session):
        self.db = db

    def create_sensor(self, sensor_data: SensorCreate) -> EnvironmentalSensor:
        """Register new environmental sensor"""
        from app.core.tenant_query import apply_tenant_filter
        from app.core.tenant import get_current_tenant_id
        from sqlalchemy.exc import IntegrityError
        
        tenant_id = get_current_tenant_id()
        
        # Check for duplicate sensor_id
        if sensor_data.sensor_id:
            query = self.db.query(EnvironmentalSensor).filter(
                EnvironmentalSensor.sensor_id == sensor_data.sensor_id
            )
            query = apply_tenant_filter(query, EnvironmentalSensor)
            existing = query.first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Environmental sensor with sensor_id '{sensor_data.sensor_id}' already exists"
                )
        
        sensor = EnvironmentalSensor(**sensor_data.model_dump())
        self.db.add(sensor)
        
        # Catch database constraint violations and convert to user-friendly errors
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            error_str = str(e).lower()
            if 'sensor_id' in error_str or 'idx_environmental_sensors_sensor_id_tenant' in error_str:
                raise HTTPException(
                    status_code=400,
                    detail=f"Environmental sensor with sensor_id '{sensor_data.sensor_id}' already exists"
                )
            raise
        
        self.db.refresh(sensor)
        return sensor

    def record_reading(self, reading_data: ReadingCreate) -> EnvironmentalReading:
        """Record sensor reading"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(EnvironmentalSensor).filter(
            EnvironmentalSensor.id == reading_data.sensor_id
        )
        query = apply_tenant_filter(query, EnvironmentalSensor)
        sensor = query.first()

        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not found")

        # Check thresholds
        is_anomaly = False
        threshold_breached = None

        if sensor.warning_threshold_min and reading_data.value < sensor.warning_threshold_min:
            is_anomaly = True
            threshold_breached = "warning"
        elif sensor.warning_threshold_max and reading_data.value > sensor.warning_threshold_max:
            is_anomaly = True
            threshold_breached = "warning"

        if sensor.critical_threshold_min and reading_data.value < sensor.critical_threshold_min:
            is_anomaly = True
            threshold_breached = "critical"
        elif sensor.critical_threshold_max and reading_data.value > sensor.critical_threshold_max:
            is_anomaly = True
            threshold_breached = "critical"

        reading = EnvironmentalReading(
            **reading_data.model_dump(),
            is_anomaly=is_anomaly,
            threshold_breached=threshold_breached
        )

        # Update sensor last reading
        sensor.last_reading_at = reading.timestamp
        sensor.last_reading_value = reading.value

        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)

        return reading

    def record_batch_readings(self, readings: List[ReadingCreate]) -> dict:
        """Record multiple readings at once"""
        recorded = 0
        for reading_data in readings:
            try:
                self.record_reading(reading_data)
                recorded += 1
            except Exception as e:
                continue

        return {"recorded": recorded, "total": len(readings)}

    def get_latest_readings(self, datacenter_id: Optional[int] = None, sensor_type: Optional[str] = None) -> List:
        """Get latest reading from each sensor"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(EnvironmentalSensor)
        query = apply_tenant_filter(query, EnvironmentalSensor)

        if datacenter_id:
            query = query.filter(EnvironmentalSensor.datacenter_id == datacenter_id)
        if sensor_type:
            query = query.filter(EnvironmentalSensor.sensor_type == sensor_type)

        sensors = query.all()

        results = []
        for sensor in sensors:
            query = self.db.query(EnvironmentalReading).filter(
                EnvironmentalReading.sensor_id == sensor.id
            )
            query = apply_tenant_filter(query, EnvironmentalReading)
            latest = query.order_by(EnvironmentalReading.timestamp.desc()).first()

            if latest:
                results.append({
                    "sensor": sensor,
                    "latest_reading": latest
                })

        return results

    def get_temperature_trends(self, datacenter_id: int, days: int) -> dict:
        """Get temperature trends"""
        from app.core.tenant_query import apply_tenant_filter
        
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get temperature sensors (tenant-scoped)
        query = self.db.query(EnvironmentalSensor).filter(
            EnvironmentalSensor.datacenter_id == datacenter_id,
            EnvironmentalSensor.sensor_type == "temperature"
        )
        query = apply_tenant_filter(query, EnvironmentalSensor)
        sensors = query.all()

        sensor_ids = [s.id for s in sensors]

        # Get readings (tenant-scoped)
        query = self.db.query(EnvironmentalReading).filter(
            EnvironmentalReading.sensor_id.in_(sensor_ids),
            EnvironmentalReading.timestamp >= cutoff
        )
        query = apply_tenant_filter(query, EnvironmentalReading)
        readings = query.order_by(EnvironmentalReading.timestamp).all()

        return {
            "datacenter_id": datacenter_id,
            "period_days": days,
            "total_readings": len(readings),
            "avg_temperature": round(sum(r.value for r in readings) / len(readings), 2) if readings else 0,
            "min_temperature": min(r.value for r in readings) if readings else 0,
            "max_temperature": max(r.value for r in readings) if readings else 0
        }

    def get_humidity_trends(self, datacenter_id: int, days: int) -> dict:
        """Get humidity trends"""
        from app.core.tenant_query import apply_tenant_filter
        
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(EnvironmentalSensor).filter(
            EnvironmentalSensor.datacenter_id == datacenter_id,
            EnvironmentalSensor.sensor_type == "humidity"
        )
        query = apply_tenant_filter(query, EnvironmentalSensor)
        sensors = query.all()

        sensor_ids = [s.id for s in sensors]

        query = self.db.query(EnvironmentalReading).filter(
            EnvironmentalReading.sensor_id.in_(sensor_ids),
            EnvironmentalReading.timestamp >= cutoff
        )
        query = apply_tenant_filter(query, EnvironmentalReading)
        readings = query.order_by(EnvironmentalReading.timestamp).all()

        return {
            "datacenter_id": datacenter_id,
            "period_days": days,
            "total_readings": len(readings),
            "avg_humidity": round(sum(r.value for r in readings) / len(readings), 2) if readings else 0,
            "min_humidity": min(r.value for r in readings) if readings else 0,
            "max_humidity": max(r.value for r in readings) if readings else 0
        }

    def get_asset_correlation(self, asset_id: int, hours: int) -> dict:
        """Correlate environmental conditions with asset location"""
        from app.models.asset import Asset
        from app.core.tenant_query import apply_tenant_filter

        query = self.db.query(Asset).filter(Asset.id == asset_id)
        query = apply_tenant_filter(query, Asset)
        asset = query.first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Find nearby sensors (tenant-scoped)
        nearby_sensors = []
        if asset.rack_id:
            query = self.db.query(EnvironmentalSensor).filter(
                EnvironmentalSensor.rack_id == asset.rack_id
            )
            query = apply_tenant_filter(query, EnvironmentalSensor)
            nearby_sensors = query.all()

        return {
            "asset_id": asset_id,
            "asset_tag": asset.asset_tag,
            "rack_id": asset.rack_id,
            "nearby_sensors": len(nearby_sensors),
            "message": "Environmental correlation analysis"
        }

    def get_active_alerts(self, datacenter_id: Optional[int] = None) -> List:
        """Get active environmental alerts"""
        # Get recent anomalies (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)

        query = self.db.query(EnvironmentalReading).filter(
            EnvironmentalReading.timestamp >= cutoff,
            EnvironmentalReading.threshold_breached.isnot(None)
        )

        if datacenter_id:
            query = query.join(EnvironmentalSensor).filter(
                EnvironmentalSensor.datacenter_id == datacenter_id
            )

        alerts = query.order_by(EnvironmentalReading.timestamp.desc()).all()

        return alerts
