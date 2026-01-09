# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Alert Service
Handles sending email alerts for various events (low stock, maintenance, warranty)
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.models.user import User
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.models.container_stock_threshold import ContainerStockThreshold
from app.core.config import settings
from app.services.email_service import get_email_service
from app.core.tenant_query import apply_tenant_filter

logger = logging.getLogger(__name__)


class AlertService:
    """Service for sending email alerts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()
    
    def get_users_to_notify(self, tenant_id: int, alert_type: str) -> List[User]:
        """Get users who should receive alerts for a given type"""
        if not settings.ENABLE_EMAIL_ALERTS:
            return []
        
        # Check if email column exists in User model (migration may not have run yet)
        try:
            # Try to query with email filter - if column doesn't exist, this will fail
            users = self.db.query(User).filter(
                User.tenant_id == tenant_id,
                User.is_active == True,
                User.email.isnot(None)
            ).all()
        except (AttributeError, Exception) as e:
            # Email column doesn't exist yet or other error - return empty list
            logger.debug(f"Email column not available or error querying users: {e}")
            return []
        
        # Filter by notification preferences
        users_to_notify = []
        for user in users:
            # Check if user has email attribute (defensive check)
            if not hasattr(user, 'email') or not user.email:
                continue
                
            prefs = user.notification_preferences or {}
            email_enabled = prefs.get("email_enabled", True)
            alert_enabled = prefs.get(alert_type, True)
            
            if email_enabled and alert_enabled:
                users_to_notify.append(user)
        
        return users_to_notify
    
    def send_low_stock_alert(
        self,
        container: StorageContainer,
        item_type_key: str,
        asset_type: str,
        manufacturer: Optional[str],
        model: Optional[str],
        current_count: int,
        threshold: int
    ) -> bool:
        """Send low stock alert for a specific item type in a container"""
        if not settings.LOW_STOCK_ALERT_ENABLED:
            return False
        
        users = self.get_users_to_notify(container.tenant_id, "low_stock")
        if not users:
            logger.info(f"No users to notify for low stock alert in container {container.id}")
            return False
        
        # Build item type description
        item_type_desc = f"{manufacturer} {model}".strip() if manufacturer or model else asset_type
        
        success_count = 0
        for user in users:
            try:
                # Defensive check for email attribute
                if not hasattr(user, 'email') or not user.email:
                    continue
                    
                success = self.email_service.send_low_stock_alert(
                    to_email=user.email,
                    container_name=container.name,
                    item_type=item_type_desc,
                    current_count=current_count,
                    threshold=threshold,
                    container_id=container.id
                )
                if success:
                    success_count += 1
            except Exception as e:
                user_email = getattr(user, 'email', 'unknown')
                logger.error(f"Error sending low stock alert to {user_email}: {e}")
        
        logger.info(f"Sent low stock alerts: {success_count}/{len(users)} successful")
        return success_count > 0
    
    def check_and_send_low_stock_alerts(self, container_id: Optional[int] = None) -> dict:
        """Check all containers for low stock and send alerts"""
        from app.services.inventory_service import get_stock_by_item_type
        
        results = {
            "containers_checked": 0,
            "alerts_sent": 0,
            "errors": []
        }
        
        # Get containers to check
        query = self.db.query(StorageContainer)
        if container_id:
            query = query.filter(StorageContainer.id == container_id)
        query = apply_tenant_filter(query, StorageContainer)
        containers = query.all()
        
        for container in containers:
            try:
                results["containers_checked"] += 1
                
                # Get stock by item type
                stock_by_type = get_stock_by_item_type(container.id, self.db, is_storage_container=True)
                
                # Check each item type for low stock
                for item_type in stock_by_type:
                    current_count = item_type.get("count", 0)
                    min_threshold = item_type.get("min_threshold")
                    
                    if min_threshold and current_count < min_threshold:
                        # Send alert
                        success = self.send_low_stock_alert(
                            container=container,
                            item_type_key=item_type.get("item_type_key", ""),
                            asset_type=item_type.get("asset_type", ""),
                            manufacturer=item_type.get("manufacturer"),
                            model=item_type.get("model"),
                            current_count=current_count,
                            threshold=min_threshold
                        )
                        if success:
                            results["alerts_sent"] += 1
                            
            except Exception as e:
                error_msg = f"Error checking container {container.id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    def send_maintenance_due_alert(
        self,
        asset: Asset,
        maintenance_type: str,
        scheduled_date: datetime
    ) -> bool:
        """Send maintenance due alert"""
        if not settings.MAINTENANCE_ALERT_ENABLED:
            return False
        
        users = self.get_users_to_notify(asset.tenant_id, "maintenance")
        if not users:
            return False
        
        success_count = 0
        for user in users:
            try:
                # Defensive check for email attribute
                if not hasattr(user, 'email') or not user.email:
                    continue
                    
                success = self.email_service.send_maintenance_due_alert(
                    to_email=user.email,
                    asset_tag=asset.asset_tag,
                    maintenance_type=maintenance_type,
                    scheduled_date=scheduled_date.strftime("%Y-%m-%d"),
                    asset_id=asset.id
                )
                if success:
                    success_count += 1
            except Exception as e:
                user_email = getattr(user, 'email', 'unknown')
                logger.error(f"Error sending maintenance alert to {user_email}: {e}")
        
        return success_count > 0
    
    def check_and_send_maintenance_alerts(self) -> dict:
        """Check for upcoming maintenance and send alerts"""
        from app.models.maintenance import Maintenance
        
        results = {
            "maintenance_checked": 0,
            "alerts_sent": 0,
            "errors": []
        }
        
        # Get maintenance due in the next 7 days
        today = datetime.utcnow().date()
        next_week = today + timedelta(days=7)
        
        query = self.db.query(Maintenance).filter(
            Maintenance.scheduled_date >= today,
            Maintenance.scheduled_date <= next_week,
            Maintenance.status == "scheduled"
        )
        query = apply_tenant_filter(query, Maintenance)
        maintenance_items = query.all()
        
        for maintenance in maintenance_items:
            try:
                results["maintenance_checked"] += 1
                
                # Get asset
                asset = self.db.query(Asset).filter(Asset.id == maintenance.asset_id).first()
                if not asset:
                    continue
                
                # Send alert
                success = self.send_maintenance_due_alert(
                    asset=asset,
                    maintenance_type=maintenance.maintenance_type or "Maintenance",
                    scheduled_date=maintenance.scheduled_date
                )
                if success:
                    results["alerts_sent"] += 1
                    
            except Exception as e:
                error_msg = f"Error checking maintenance {maintenance.id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    def send_warranty_expiring_alert(
        self,
        asset: Asset,
        warranty_expiry: datetime,
        days_remaining: int
    ) -> bool:
        """Send warranty expiring alert"""
        if not settings.WARRANTY_ALERT_ENABLED:
            return False
        
        users = self.get_users_to_notify(asset.tenant_id, "warranty")
        if not users:
            return False
        
        success_count = 0
        for user in users:
            try:
                # Defensive check for email attribute
                if not hasattr(user, 'email') or not user.email:
                    continue
                    
                success = self.email_service.send_warranty_expiring_alert(
                    to_email=user.email,
                    asset_tag=asset.asset_tag,
                    warranty_expiry=warranty_expiry.strftime("%Y-%m-%d"),
                    days_remaining=days_remaining,
                    asset_id=asset.id
                )
                if success:
                    success_count += 1
            except Exception as e:
                user_email = getattr(user, 'email', 'unknown')
                logger.error(f"Error sending warranty alert to {user_email}: {e}")
        
        return success_count > 0
    
    def check_and_send_warranty_alerts(self) -> dict:
        """Check for expiring warranties and send alerts"""
        results = {
            "assets_checked": 0,
            "alerts_sent": 0,
            "errors": []
        }
        
        # Get assets with warranty expiring in the next 30 days
        today = datetime.utcnow().date()
        warning_date = today + timedelta(days=settings.WARRANTY_WARNING_DAYS)
        
        query = self.db.query(Asset).filter(
            Asset.warranty_end_date.isnot(None),
            Asset.warranty_end_date >= today,
            Asset.warranty_end_date <= warning_date
        )
        query = apply_tenant_filter(query, Asset)
        assets = query.all()
        
        for asset in assets:
            try:
                results["assets_checked"] += 1
                
                if not asset.warranty_end_date:
                    continue
                
                days_remaining = (asset.warranty_end_date - today).days
                
                # Send alert
                success = self.send_warranty_expiring_alert(
                    asset=asset,
                    warranty_expiry=asset.warranty_end_date,
                    days_remaining=days_remaining
                )
                if success:
                    results["alerts_sent"] += 1
                    
            except Exception as e:
                error_msg = f"Error checking warranty for asset {asset.id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results

