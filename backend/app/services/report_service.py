# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Report Service - Business Logic
Generate reports, exports, and analytics
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from io import BytesIO

from app.models.asset import Asset, AssetStatus
from app.models.location import Datacenter, Rack
from app.models.maintenance import MaintenanceRecord


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def asset_utilization_report(self, datacenter_id: Optional[int] = None, asset_type: Optional[str] = None) -> dict:
        """Generate asset utilization report"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Asset)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, Asset)

        if datacenter_id:
            query = query.filter(Asset.datacenter_id == datacenter_id)
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)

        total_assets = query.count()
        active_assets = query.filter(Asset.status == AssetStatus.ACTIVE).count()
        deployed_assets = query.filter(Asset.status == AssetStatus.DEPLOYED).count()
        maintenance_assets = query.filter(Asset.status == AssetStatus.MAINTENANCE).count()
        failed_assets = query.filter(Asset.status == AssetStatus.FAILED).count()

        return {
            "total_assets": total_assets,
            "active": active_assets,
            "deployed": deployed_assets,
            "maintenance": maintenance_assets,
            "failed": failed_assets,
            "utilization_rate": round((active_assets + deployed_assets) / total_assets * 100, 2) if total_assets > 0 else 0
        }

    def capacity_summary(self, datacenter_id: Optional[int] = None) -> dict:
        """Generate capacity summary"""
        from app.services.location_service import LocationService
        from app.core.tenant_query import apply_tenant_filter

        loc_service = LocationService(self.db)

        query = self.db.query(Rack)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, Rack)
        if datacenter_id:
            query = query.filter(Rack.datacenter_id == datacenter_id)

        racks = query.all()

        total_u_space = sum(r.height_u for r in racks)
        total_power_capacity = sum(r.power_capacity_watts or 0 for r in racks)

        used_u_space = 0
        used_power = 0

        for rack in racks:
            try:
                capacity = loc_service.get_rack_capacity(rack.id)
                used_u_space += capacity.used_u_space
                used_power += capacity.used_power_watts
            except Exception:
                continue

        return {
            "total_racks": len(racks),
            "space": {
                "total_u": total_u_space,
                "used_u": used_u_space,
                "available_u": total_u_space - used_u_space,
                "utilization_percent": round(used_u_space / total_u_space * 100, 2) if total_u_space > 0 else 0
            },
            "power": {
                "total_watts": total_power_capacity,
                "used_watts": used_power,
                "available_watts": total_power_capacity - used_power,
                "utilization_percent": round(used_power / total_power_capacity * 100, 2) if total_power_capacity > 0 else 0
            }
        }

    def inventory_value_report(self, datacenter_id: Optional[int] = None) -> dict:
        """Generate inventory value report"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Asset).filter(Asset.purchase_cost.isnot(None))
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, Asset)

        if datacenter_id:
            query = query.filter(Asset.datacenter_id == datacenter_id)

        assets = query.all()
        total_value = sum(asset.purchase_cost or 0 for asset in assets)

        return {
            "total_assets_valued": len(assets),
            "total_purchase_value": round(total_value, 2),
            "currency": "USD",
            "average_asset_value": round(total_value / len(assets), 2) if assets else 0
        }

    def pue_report(self, datacenter_id: int, days: int) -> dict:
        """Generate PUE report"""
        # Simplified PUE calculation (requires actual power monitoring data)
        return {
            "datacenter_id": datacenter_id,
            "period_days": days,
            "average_pue": 1.5,  # Placeholder
            "message": "PUE calculation requires power monitoring integration"
        }

    def lifecycle_status_report(self, datacenter_id: Optional[int] = None) -> dict:
        """Generate lifecycle status report"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Asset)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, Asset)

        if datacenter_id:
            query = query.filter(Asset.datacenter_id == datacenter_id)

        status_counts = {}
        for status in AssetStatus:
            count = query.filter(Asset.status == status).count()
            status_counts[status.value] = count

        return {
            "datacenter_id": datacenter_id,
            "status_breakdown": status_counts,
            "total_assets": sum(status_counts.values())
        }

    def maintenance_summary_report(self, days: int, datacenter_id: Optional[int] = None) -> dict:
        """Generate maintenance summary"""
        from app.core.tenant_query import apply_tenant_filter
        
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(MaintenanceRecord).filter(MaintenanceRecord.created_at >= cutoff)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, MaintenanceRecord)

        if datacenter_id:
            query = query.join(Asset).filter(Asset.datacenter_id == datacenter_id)

        records = query.all()

        return {
            "period_days": days,
            "total_maintenance_records": len(records),
            "completed": len([r for r in records if r.status.value == "completed"]),
            "in_progress": len([r for r in records if r.status.value == "in_progress"]),
            "scheduled": len([r for r in records if r.status.value == "scheduled"])
        }

    def environmental_compliance_report(self, datacenter_id: int, days: int) -> dict:
        """Generate environmental compliance report"""
        return {
            "datacenter_id": datacenter_id,
            "period_days": days,
            "message": "Environmental compliance reporting requires sensor data"
        }

    def audit_trail_report(self, asset_id: Optional[int] = None, days: int = 30) -> dict:
        """Generate audit trail"""
        from app.models.asset import AssetLifecycleEvent
        from app.core.tenant_query import apply_tenant_filter

        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(AssetLifecycleEvent).filter(AssetLifecycleEvent.event_timestamp >= cutoff)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, AssetLifecycleEvent)

        if asset_id:
            query = query.filter(AssetLifecycleEvent.asset_id == asset_id)

        events = query.order_by(AssetLifecycleEvent.event_timestamp.desc()).all()

        return {
            "total_events": len(events),
            "period_days": days,
            "events": events[:100]  # Limit to 100 most recent
        }

    def export_inventory_xlsx(self, datacenter_id: Optional[int] = None) -> tuple:
        """Export inventory to Excel"""
        # In production, use openpyxl to generate actual Excel file
        return (b"", "inventory_export.xlsx")

    def export_inventory_csv(self, datacenter_id: Optional[int] = None) -> tuple:
        """Export inventory to CSV"""
        return (b"", "inventory_export.csv")

    def export_inventory_pdf(self, datacenter_id: Optional[int] = None) -> tuple:
        """Export inventory to PDF"""
        return (b"", "inventory_export.pdf")

    def export_ptouch_csv(self, datacenter_id: Optional[int] = None) -> tuple:
        """
        Export inventory to CSV format compatible with Brother P-Touch Editor
        Columns: Asset Tag, Manufacturer, Model, Serial Number, QR Data
        """
        import csv
        import json
        from io import StringIO
        from app.core.tenant_query import apply_tenant_filter

        query = self.db.query(Asset)
        # Apply tenant filter FIRST
        query = apply_tenant_filter(query, Asset)
        if datacenter_id:
            query = query.filter(Asset.datacenter_id == datacenter_id)
        
        assets = query.all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow(['Asset Tag', 'Manufacturer', 'Model', 'Serial Number', 'QR Data'])
        
        for asset in assets:
            # Generate QR data JSON
            qr_data = {
                "id": asset.id,
                "asset_tag": asset.asset_tag,
                "serial_number": asset.serial_number,
                "asset_type": asset.asset_type,
                "manufacturer": asset.manufacturer,
                "model": asset.model
            }
            
            writer.writerow([
                asset.asset_tag,
                asset.manufacturer,
                asset.model,
                asset.serial_number,
                json.dumps(qr_data)
            ])
            
        return (output.getvalue().encode('utf-8'), "ptouch_export.csv")

    def dashboard_summary(self, datacenter_id: Optional[int] = None) -> dict:
        """Get dashboard summary statistics including asset counts by type, low stock items, and upcoming maintenance"""
        from app.core.tenant_query import apply_tenant_filter
        from app.models.asset_type import AssetTypeModel
        from app.services.inventory_service import get_container_stock_summary
        from app.models.maintenance import MaintenanceRecord, MaintenanceStatus
        
        asset_util = self.asset_utilization_report(datacenter_id)
        capacity = self.capacity_summary(datacenter_id)
        inventory_value = self.inventory_value_report(datacenter_id)

        # Asset count by type
        asset_type_query = self.db.query(Asset.asset_type, func.count(Asset.id).label('count'))
        asset_type_query = apply_tenant_filter(asset_type_query, Asset)
        if datacenter_id:
            asset_type_query = asset_type_query.filter(Asset.datacenter_id == datacenter_id)
        asset_type_query = asset_type_query.group_by(Asset.asset_type)
        asset_type_counts = asset_type_query.all()
        
        # Get asset type display names
        asset_types_map = {}
        asset_types_query = self.db.query(AssetTypeModel)
        asset_types_query = apply_tenant_filter(asset_types_query, AssetTypeModel)
        for at in asset_types_query.all():
            asset_types_map[at.name] = at.display_name
        
        asset_counts_by_type = []
        for asset_type, count in asset_type_counts:
            asset_counts_by_type.append({
                "asset_type": asset_type,
                "display_name": asset_types_map.get(asset_type, asset_type),
                "count": count
            })
        asset_counts_by_type.sort(key=lambda x: x['count'], reverse=True)

        # Low stock items - check both StorageContainers and Assets with stock thresholds
        from app.models.storage_container import StorageContainer
        from app.services.inventory_service import get_container_stock_info

        low_stock_items = []

        # Check StorageContainers with min_stock_threshold set
        storage_containers_query = self.db.query(StorageContainer).filter(
            StorageContainer.min_stock_threshold.isnot(None),
            StorageContainer.min_stock_threshold > 0
        )
        storage_containers_query = apply_tenant_filter(storage_containers_query, StorageContainer)
        if datacenter_id:
            storage_containers_query = storage_containers_query.filter(StorageContainer.datacenter_id == datacenter_id)
        storage_containers = storage_containers_query.all()

        for container in storage_containers:
            stock_summary = get_container_stock_summary(container.id, self.db, is_storage_container=True)
            if stock_summary and stock_summary.get('is_low_stock', False):
                low_stock_items.append({
                    "container_id": container.id,
                    "container_name": stock_summary.get('container_name', container.name),
                    "current_count": stock_summary.get('total_items', 0),
                    "min_threshold": stock_summary.get('min_threshold', 0),
                    "low_stock_types": stock_summary.get('low_stock_types', [])
                })

        # Also check Asset-based storage boxes with min_stock_threshold set
        asset_boxes_query = self.db.query(Asset).filter(
            Asset.min_stock_threshold.isnot(None),
            Asset.min_stock_threshold > 0
        )
        asset_boxes_query = apply_tenant_filter(asset_boxes_query, Asset)
        if datacenter_id:
            asset_boxes_query = asset_boxes_query.filter(Asset.datacenter_id == datacenter_id)
        asset_boxes = asset_boxes_query.all()

        for box in asset_boxes:
            stock_info = get_container_stock_info(box.id, self.db)
            if stock_info and stock_info.get('is_low_stock', False):
                low_stock_items.append({
                    "container_id": box.id,
                    "container_name": stock_info.get('container_name', box.asset_tag),
                    "current_count": stock_info.get('current_count', 0),
                    "min_threshold": stock_info.get('min_threshold', 0),
                    "low_stock_types": []  # Asset-based boxes don't track by type
                })

        # Upcoming maintenance - scheduled and in_progress records
        upcoming_maintenance_query = self.db.query(MaintenanceRecord).filter(
            MaintenanceRecord.status.in_([MaintenanceStatus.SCHEDULED, MaintenanceStatus.IN_PROGRESS])
        )
        upcoming_maintenance_query = apply_tenant_filter(upcoming_maintenance_query, MaintenanceRecord)
        
        # Filter by scheduled_date if available, or get all scheduled/in_progress
        upcoming_maintenance = []
        for record in upcoming_maintenance_query.all():
            # Get asset info
            asset_query = self.db.query(Asset).filter(Asset.id == record.asset_id)
            asset_query = apply_tenant_filter(asset_query, Asset)
            asset = asset_query.first()
            
            if datacenter_id and asset and asset.datacenter_id != datacenter_id:
                continue
            
            upcoming_maintenance.append({
                "id": record.id,
                "asset_id": record.asset_id,
                "asset_tag": asset.asset_tag if asset else "Unknown",
                "title": record.title,
                "scheduled_date": record.scheduled_date.isoformat() if record.scheduled_date else None,
                "status": record.status.value,
                "priority": record.priority.value if record.priority else None,
                "maintenance_type": record.maintenance_type.value if record.maintenance_type else None
            })
        
        # Sort by scheduled_date (earliest first), then by priority
        upcoming_maintenance.sort(key=lambda x: (
            x['scheduled_date'] if x['scheduled_date'] else '9999-12-31',
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.get('priority', 'medium'), 2)
        ))

        return {
            "asset_utilization": asset_util,
            "capacity": capacity,
            "inventory_value": inventory_value,
            "asset_counts_by_type": asset_counts_by_type,
            "low_stock_items": low_stock_items,
            "upcoming_maintenance": upcoming_maintenance[:10],  # Limit to top 10
            "timestamp": datetime.utcnow().isoformat()
        }

    def admin_dashboard_summary(self) -> dict:
        """Get system-wide dashboard summary for super admins (aggregates across all tenants)"""
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.models.storage_container import StorageContainer
        from app.models.location import Datacenter
        
        # Get all tenants (skip tenant filter for admin view)
        total_tenants = self.db.query(Tenant).execution_options(skip_tenant_filter=True).count()
        active_tenants = self.db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
            Tenant.is_active == True
        ).count()
        
        # Get all users (skip tenant filter)
        total_users = self.db.query(User).execution_options(skip_tenant_filter=True).count()
        active_users = self.db.query(User).execution_options(skip_tenant_filter=True).filter(
            User.is_active == True
        ).count()
        
        # Get all assets (skip tenant filter)
        total_assets = self.db.query(Asset).execution_options(skip_tenant_filter=True).count()
        active_assets = self.db.query(Asset).execution_options(skip_tenant_filter=True).filter(
            Asset.status == AssetStatus.ACTIVE
        ).count()
        deployed_assets = self.db.query(Asset).execution_options(skip_tenant_filter=True).filter(
            Asset.status == AssetStatus.DEPLOYED
        ).count()
        
        # Get all racks (skip tenant filter)
        total_racks = self.db.query(Rack).execution_options(skip_tenant_filter=True).count()
        
        # Get all storage containers (skip tenant filter)
        total_storage_containers = self.db.query(StorageContainer).execution_options(skip_tenant_filter=True).count()
        
        # Get all datacenters (skip tenant filter)
        total_datacenters = self.db.query(Datacenter).execution_options(skip_tenant_filter=True).count()
        
        # Get tenant breakdown (top 10 tenants by asset count)
        tenant_breakdown = []
        tenants = self.db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
            Tenant.id != 1  # Exclude admin tenant
        ).all()
        
        for tenant in tenants:
            asset_count = self.db.query(Asset).execution_options(skip_tenant_filter=True).filter(
                Asset.tenant_id == tenant.id
            ).count()
            user_count = self.db.query(User).execution_options(skip_tenant_filter=True).filter(
                User.tenant_id == tenant.id
            ).count()
            
            if asset_count > 0 or user_count > 0:  # Only include tenants with data
                tenant_breakdown.append({
                    "id": tenant.id,
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "is_active": tenant.is_active,
                    "asset_count": asset_count,
                    "user_count": user_count,
                    "subscription_tier": tenant.subscription_tier
                })
        
        # Sort by asset count descending
        tenant_breakdown.sort(key=lambda x: x['asset_count'], reverse=True)
        
        # Get total inventory value across all tenants
        total_value = self.db.query(func.sum(Asset.purchase_cost)).execution_options(
            skip_tenant_filter=True
        ).filter(
            Asset.purchase_cost.isnot(None)
        ).scalar() or 0
        
        return {
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "inactive": total_tenants - active_tenants
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users
            },
            "assets": {
                "total": total_assets,
                "active": active_assets,
                "deployed": deployed_assets,
                "other": total_assets - active_assets - deployed_assets
            },
            "infrastructure": {
                "datacenters": total_datacenters,
                "racks": total_racks,
                "storage_containers": total_storage_containers
            },
            "inventory_value": {
                "total_purchase_value": float(total_value)
            },
            "tenant_breakdown": tenant_breakdown[:10],  # Top 10 tenants
            "timestamp": datetime.utcnow().isoformat()
        }

    def depreciation_schedule(self, datacenter_id: Optional[int] = None) -> dict:
        """Generate depreciation schedule"""
        # Simplified depreciation calculation
        return {
            "message": "Depreciation schedule calculation",
            "datacenter_id": datacenter_id
        }
