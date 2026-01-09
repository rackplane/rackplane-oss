# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Maintenance Service - Business Logic
Maintenance tracking and predictive analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Optional
import random

from app.models.maintenance import MaintenanceRecord, MaintenancePrediction
from app.models.asset import Asset
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate


class MaintenanceService:
    def __init__(self, db: Session):
        self.db = db

    def create_maintenance(self, maintenance_data: MaintenanceCreate) -> MaintenanceRecord:
        """Create maintenance record"""
        from app.core.tenant_query import apply_tenant_filter
        
        # Verify asset exists (tenant-scoped)
        query = self.db.query(Asset).filter(Asset.id == maintenance_data.asset_id)
        query = apply_tenant_filter(query, Asset)
        asset = query.first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        record = MaintenanceRecord(**maintenance_data.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_maintenance(self, maintenance_id: int, update_data: MaintenanceUpdate) -> MaintenanceRecord:
        """Update maintenance record"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id)
        query = apply_tenant_filter(query, MaintenanceRecord)
        record = query.first()
        if not record:
            raise HTTPException(status_code=404, detail="Maintenance record not found")

        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(record, key, value)

        record.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(record)
        return record

    def generate_predictions(self, asset_id: Optional[int] = None) -> dict:
        """Generate predictive maintenance predictions using ML"""
        from app.core.tenant_query import apply_tenant_filter
        
        # This is a simplified version - in production, this would use actual ML models
        query = self.db.query(Asset)
        query = apply_tenant_filter(query, Asset)
        if asset_id:
            query = query.filter(Asset.id == asset_id)

        assets = query.all()
        predictions_created = 0

        for asset in assets:
            # Simple heuristic-based prediction (replace with actual ML in production)
            if asset.deployed_at:
                days_deployed = (datetime.utcnow() - asset.deployed_at).days

                # Example: Predict PSU failure for servers > 3 years old
                if days_deployed > 1095 and asset.asset_type.value == "server":
                    confidence = min(0.7 + (days_deployed - 1095) / 365 * 0.2, 0.95)

                    prediction = MaintenancePrediction(
                        asset_id=asset.id,
                        prediction_date=datetime.utcnow(),
                        predicted_failure_date=datetime.utcnow() + timedelta(days=random.randint(30, 180)),
                        confidence_score=confidence,
                        failure_type="psu",
                        failure_severity="high",
                        recommended_action=f"Schedule PSU replacement for {asset.asset_tag}",
                        estimated_mttr_hours=2.0,
                        ml_model_version="v1.0-heuristic"
                    )
                    self.db.add(prediction)
                    predictions_created += 1

        self.db.commit()

        return {
            "predictions_generated": predictions_created,
            "assets_analyzed": len(assets)
        }

    def get_mttr_analytics(self, asset_type: Optional[str] = None, days: int = 90) -> dict:
        """Calculate MTTR analytics"""
        from app.core.tenant_query import apply_tenant_filter
        
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.completed_at >= cutoff,
            MaintenanceRecord.mttr_minutes.isnot(None)
        )
        query = apply_tenant_filter(query, MaintenanceRecord)

        if asset_type:
            query = query.join(Asset).filter(Asset.asset_type == asset_type)

        records = query.all()

        if not records:
            return {
                "total_records": 0,
                "mean_mttr_minutes": 0,
                "median_mttr_minutes": 0
            }

        mttr_values = [r.mttr_minutes for r in records]
        mttr_values.sort()

        return {
            "total_records": len(records),
            "mean_mttr_minutes": round(sum(mttr_values) / len(mttr_values), 2),
            "median_mttr_minutes": mttr_values[len(mttr_values) // 2],
            "min_mttr_minutes": min(mttr_values),
            "max_mttr_minutes": max(mttr_values)
        }
