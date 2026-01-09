# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Asset Service - Business Logic
Handles asset lifecycle, photo uploads, and deployments
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from datetime import datetime
import os
import uuid

from app.models.asset import Asset, AssetLifecycleEvent, AssetStatus
from app.schemas.asset import AssetCreate, AssetUpdate
from app.core.config import settings
from fastapi import HTTPException


class AssetService:
    def __init__(self, db: Session):
        self.db = db

    def create_asset(self, asset_data: AssetCreate) -> Asset:
        """Create a new asset"""
        from app.core.tenant_query import apply_tenant_filter
        from app.core.tenant import get_current_tenant_id
        from app.services.serial_service import generate_serial_number, generate_asset_tag
        
        # Auto-generate serial number and asset tag if not provided
        tenant_id = get_current_tenant_id()
        was_serial_auto_generated = False
        if not asset_data.serial_number:
            asset_data.serial_number = generate_serial_number(self.db, asset_data.asset_type, tenant_id)
            was_serial_auto_generated = True
        if not asset_data.asset_tag:
            asset_data.asset_tag = generate_asset_tag(self.db, asset_data.asset_type, tenant_id)
        
        # Check for duplicates (asset_tag, serial_number, hostname)
        query = self.db.query(Asset).filter(
            (Asset.asset_tag == asset_data.asset_tag) |
            (Asset.serial_number == asset_data.serial_number)
        )
        query = apply_tenant_filter(query, Asset)
        existing = query.first()

        if existing:
            if existing.asset_tag == asset_data.asset_tag:
                raise HTTPException(status_code=400, detail="Asset with this tag already exists")
            elif existing.serial_number == asset_data.serial_number:
                raise HTTPException(status_code=400, detail="Asset with this serial number already exists")
            else:
                raise HTTPException(status_code=400, detail="Asset with this tag or serial number already exists")
        
        # Check for duplicate hostname (if hostname is provided)
        if asset_data.hostname:
            hostname_query = self.db.query(Asset).filter(Asset.hostname == asset_data.hostname)
            hostname_query = apply_tenant_filter(hostname_query, Asset)
            existing_hostname = hostname_query.first()
            if existing_hostname:
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset with hostname '{asset_data.hostname}' already exists"
                )

        # Create asset - ensure status is properly converted to enum
        # Get the status directly from the validated model, not from model_dump
        # The validator should have already normalized it
        status_enum = asset_data.status  # This is already validated and normalized
        
        # AUTO-SET STATUS: If container_id is set, automatically set status to IN_STORAGE
        # VALIDATE: Prevent circular references (asset containing itself)
        if asset_data.container_id is not None:
            # Note: For new assets, we can't check for cycles yet (asset doesn't have an ID)
            # But we can at least validate the container exists
            container_query = self.db.query(Asset).filter(Asset.id == asset_data.container_id)
            container_query = apply_tenant_filter(container_query, Asset)
            container = container_query.first()
            
            if not container:
                raise HTTPException(
                    status_code=404,
                    detail=f"Container with ID {asset_data.container_id} not found"
                )
            
            status_enum = AssetStatus.IN_STORAGE
        
        # Validate that cables cannot have min_stock_threshold
        # Cables go INTO storage boxes, they are not storage boxes themselves
        asset_type_lower = (asset_data.asset_type or "").lower()
        is_cable = (
            asset_type_lower.endswith('_cable') or
            asset_type_lower in ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
        )
        if is_cable and asset_data.min_stock_threshold is not None:
            raise HTTPException(
                status_code=400,
                detail="Cables cannot have min_stock_threshold. Cables should be placed inside storage boxes, not act as storage boxes themselves."
            )
        
        # NOTE: min_stock_threshold on Asset is deprecated for non-cable assets
        # Stock thresholds are now managed via ContainerStockThreshold records for StorageContainer objects
        # We still accept the field for backward compatibility but it's ignored
        if asset_data.min_stock_threshold is not None:
            # Log a deprecation warning but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Asset.min_stock_threshold is deprecated. Use ContainerStockThreshold for StorageContainer objects instead. "
                f"Field will be ignored for asset: {asset_data.asset_tag}"
            )
        
        # Create asset dict, but manually set status to ensure it's the enum, not a string
        asset_dict = {k: v for k, v in asset_data.model_dump(mode='python').items() if k != 'status'}
        
        # TRANSITIONAL: Handle connector types by mapping them to custom_fields
        # The Asset table doesn't have these columns yet (NetworkCable does), so we stash them in custom_fields
        conn_a = asset_dict.pop('connector_type_end_a', None)
        conn_b = asset_dict.pop('connector_type_end_b', None)
        
        if conn_a or conn_b:
            if 'custom_fields' not in asset_dict or asset_dict['custom_fields'] is None:
                asset_dict['custom_fields'] = {}
            
            if conn_a: asset_dict['custom_fields']['connector_type_end_a'] = conn_a
            if conn_b: asset_dict['custom_fields']['connector_type_end_b'] = conn_b
            
        # Force status to be the enum value (not string) - use the enum directly
        asset_dict['status'] = status_enum
        asset = Asset(**asset_dict)
        
        # Set original_serial_number if serial was auto-generated
        # This allows QR codes to still match after serial number is updated
        if was_serial_auto_generated and not asset.original_serial_number:
            asset.original_serial_number = asset.serial_number
        
        # CRITICAL FIX: Force SQLAlchemy to use the enum value, not the name
        # After creating the asset, explicitly set status to ensure it uses the value
        if hasattr(asset, 'status') and asset.status is not None:
            status_value = asset.status.value if isinstance(asset.status, AssetStatus) else str(asset.status).lower()
            asset.status = AssetStatus(status_value)
        self.db.add(asset)
        
        # Catch database constraint violations and convert to user-friendly errors
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Check if it's a unique constraint violation (IntegrityError)
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError):
                error_str = str(e).lower()
                if 'hostname' in error_str or 'idx_assets_hostname_tenant' in error_str:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Asset with hostname '{asset_data.hostname}' already exists"
                    )
                elif 'asset_tag' in error_str or 'idx_assets_tag_tenant' in error_str:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Asset with tag '{asset_data.asset_tag}' already exists"
                    )
                elif 'serial_number' in error_str or 'idx_assets_serial_tenant' in error_str:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Asset with serial number '{asset_data.serial_number}' already exists"
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Asset with duplicate information already exists"
                    )
            # Re-raise if it's not a constraint violation
            raise
        
        self.db.refresh(asset)

        # AUTO-CREATE/UPDATE STORAGE BOX: If this is a cable, automatically create/update its storage box
        # BUT only if:
        # 1. Cable is in storage (don't override user's explicit status choice)
        # 2. User did NOT explicitly provide a container_id (respect user's explicit assignment)
        asset_type_lower = (asset.asset_type or '').lower()
        is_cable = (
            'cable' in asset_type_lower or
            asset_type_lower in ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
        )
        if is_cable and asset.status == AssetStatus.IN_STORAGE and not asset_data.container_id:
            # Only auto-sync storage box if:
            # - Cable is explicitly in storage status
            # - User didn't explicitly provide a container_id
            # This prevents overriding user's explicit choices
            try:
                from app.services.stock_service import sync_storage_box_for_cable
                sync_storage_box_for_cable(self.db, asset)
            except Exception as e:
                # Log but don't fail asset creation if box sync fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to sync storage box for cable {asset.asset_tag} (ID: {asset.id}): {str(e)}")

        # Create lifecycle event
        event = AssetLifecycleEvent(
            asset_id=asset.id,
            event_type="created",
            event_timestamp=datetime.utcnow(),
            new_status=asset.status.value,
            notes="Asset created in system"
        )
        self.db.add(event)
        self.db.commit()

        return asset

    def update_asset(self, asset_id: int, asset_update: AssetUpdate) -> Asset:
        """Update asset information with collision detection for rack positions"""
        from app.core.tenant_query import apply_tenant_filter
        
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        old_status = asset.status

        # Get update dict early to check for rack_position_end and potentially modify it
        update_dict = asset_update.model_dump(exclude_unset=True, mode='python')
        
        # Collision detection for rack position updates
        if asset_update.rack_id is not None or asset_update.rack_position_start is not None:
            rack_id = asset_update.rack_id if asset_update.rack_id is not None else asset.rack_id
            start_u = asset_update.rack_position_start if asset_update.rack_position_start is not None else asset.rack_position_start
            height_u = asset_update.height_u if asset_update.height_u is not None else asset.height_u or 1
            
            if rack_id and start_u:
                # Calculate end position
                end_u = start_u + height_u - 1
                
                # Check for collisions with other assets in the same rack
                query = self.db.query(Asset).filter(
                    Asset.rack_id == rack_id,
                    Asset.id != asset_id  # Exclude the current asset
                )
                query = apply_tenant_filter(query, Asset)
                existing_assets = query.all()
                
                for existing_asset in existing_assets:
                    if existing_asset.rack_position_start and existing_asset.rack_position_end:
                        # Check for overlap: [start_u, end_u] overlaps with [existing_start, existing_end]
                        existing_start = existing_asset.rack_position_start
                        existing_end = existing_asset.rack_position_end
                        
                        if not (end_u < existing_start or start_u > existing_end):
                            raise HTTPException(
                                status_code=400,
                                detail=f"Position U{start_u}-{end_u} conflicts with {existing_asset.asset_tag} at U{existing_start}-{existing_end}. Please choose a different position."
                            )
                    elif existing_asset.rack_position_start:
                        # Single U device
                        if start_u <= existing_asset.rack_position_start <= end_u:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Position U{start_u}-{end_u} conflicts with {existing_asset.asset_tag} at U{existing_asset.rack_position_start}. Please choose a different position."
                            )
                
                # Auto-calculate rack_position_end if not provided
                if 'rack_position_end' not in update_dict or update_dict.get('rack_position_end') is None:
                    # Set rack_position_end in the update dict (will be applied later)
                    update_dict['rack_position_end'] = end_u

        # TRANSITIONAL: Handle connector types by mapping them to custom_fields
        # The Asset table doesn't have these columns yet, so we map them to custom_fields for persistence
        conn_a = update_dict.pop('connector_type_end_a', None)
        conn_b = update_dict.pop('connector_type_end_b', None)
        
        if conn_a is not None or conn_b is not None:
            # We need to explicitly handle custom_fields merge because we are modifying the dict
            # Get current custom_fields
            current_custom_fields = dict(asset.custom_fields) if asset.custom_fields else {}
            
            # If update_dict already has custom_fields (from request), use that as base for merge
            if 'custom_fields' in update_dict and update_dict['custom_fields'] is not None:
                current_custom_fields.update(update_dict['custom_fields'])
            
            # Update with connector types
            if conn_a is not None: current_custom_fields['connector_type_end_a'] = conn_a
            if conn_b is not None: current_custom_fields['connector_type_end_b'] = conn_b
            
            # Set back to update_dict
            update_dict['custom_fields'] = current_custom_fields

        # Update fields - ensure status is properly converted to enum
        # Get status separately to ensure it's the enum object, not a string
        status_to_update = None
        if asset_update.status is not None:
            status_to_update = asset_update.status  # Already validated enum
        
        # Remove status from update_dict (we handle it separately)
        update_dict.pop('status', None)
        
        # AUTO-SET STATUS: If container_id or storage_container_id is being set, automatically set status to IN_STORAGE
        container_id_being_set = 'container_id' in update_dict and update_dict['container_id'] is not None
        container_id_cleared = 'container_id' in update_dict and update_dict['container_id'] is None
        storage_container_id_being_set = 'storage_container_id' in update_dict and update_dict['storage_container_id'] is not None
        storage_container_id_cleared = 'storage_container_id' in update_dict and update_dict['storage_container_id'] is None
        
        # VALIDATE: Prevent circular references (asset containing itself or creating cycles)
        if container_id_being_set:
            new_container_id = update_dict['container_id']
            
            # Prevent asset from containing itself
            if new_container_id == asset_id:
                raise HTTPException(
                    status_code=400,
                    detail="An asset cannot be placed inside itself. Please select a different container."
                )
            
            # Prevent circular references (container containing its parent)
            # Check if the new container is a descendant of this asset
            def is_descendant(container_id: int, ancestor_id: int, visited: set = None) -> bool:
                """Check if container_id is a descendant of ancestor_id (prevents cycles)"""
                if visited is None:
                    visited = set()
                
                if container_id in visited:
                    return False  # Already checked this path
                
                visited.add(container_id)
                
                if container_id == ancestor_id:
                    return True  # Found cycle
                
                # Get the container asset
                container_query = self.db.query(Asset).filter(Asset.id == container_id)
                container_query = apply_tenant_filter(container_query, Asset)
                container_asset = container_query.first()
                
                if not container_asset or not container_asset.container_id:
                    return False  # No parent, no cycle
                
                # Recursively check parent
                return is_descendant(container_asset.container_id, ancestor_id, visited)
            
            if is_descendant(new_container_id, asset_id):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot create circular reference. The selected container is a descendant of this asset."
                )
            
            # If container_id is being set, auto-set status to IN_STORAGE
            status_to_update = AssetStatus.IN_STORAGE
        
        # AUTO-SET STATUS: If storage_container_id is being set, automatically set status to IN_STORAGE
        # This ensures items placed in storage containers are tracked correctly for stock management
        if storage_container_id_being_set:
            status_to_update = AssetStatus.IN_STORAGE
        elif storage_container_id_cleared and asset.storage_container_id is not None:
            # If storage_container_id is being cleared, don't auto-change status
            # (user might want to keep the status or set it manually)
            pass
        
        if container_id_cleared and asset.container_id is not None:
            # If container_id is being cleared and it was previously set, don't auto-change status
            # (user might want to keep the status or set it manually)
            pass
        
        # NOTE: min_stock_threshold on Asset is deprecated
        # Stock thresholds are now managed via ContainerStockThreshold records for StorageContainer objects
        # We still accept the field for backward compatibility but it's ignored
        if 'min_stock_threshold' in update_dict and update_dict['min_stock_threshold'] is not None:
            # Log a deprecation warning but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Asset.min_stock_threshold is deprecated. Use ContainerStockThreshold for StorageContainer objects instead. "
                f"Field will be ignored for asset: {asset.asset_tag}"
            )
        
        # Preserve original_serial_number when updating serial_number
        # If original_serial_number is not set and serial_number is being updated,
        # set original_serial_number to the current serial_number before updating
        if 'serial_number' in update_dict and update_dict['serial_number'] != asset.serial_number:
            if not asset.original_serial_number:
                # This is the first time serial_number is being updated, preserve the original
                asset.original_serial_number = asset.serial_number
        
        # Update all fields except status
        for key, value in update_dict.items():
            setattr(asset, key, value)
        
        # Set status separately as the enum object
        # CRITICAL: Always use the enum value, not the name, when setting
        if status_to_update is not None:
            # Explicitly convert to enum if it's a string, or use the enum directly
            if isinstance(status_to_update, str):
                # Convert string to enum using the value
                asset.status = AssetStatus(status_to_update.lower())
            elif isinstance(status_to_update, AssetStatus):
                # Use the enum directly - SQLAlchemy will use the value
                asset.status = status_to_update
            else:
                # Fallback: try to get the value
                asset.status = AssetStatus(status_to_update.value if hasattr(status_to_update, 'value') else str(status_to_update).lower())
        
        # CRITICAL FIX: Force SQLAlchemy to use the enum value by explicitly setting it
        # SQLAlchemy with native enums uses the enum name, so we need to ensure it uses the value
        if hasattr(asset, 'status') and asset.status is not None:
            # Get the value explicitly and ensure it's set correctly
            status_value = asset.status.value if isinstance(asset.status, AssetStatus) else str(asset.status).lower()
            # Re-assign to ensure SQLAlchemy binds the value, not the name
            asset.status = AssetStatus(status_value)

        asset.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(asset)

        # AUTO-CREATE/UPDATE STORAGE BOX: If this is a cable, automatically create/update its storage box
        # BUT: Skip if container_id was explicitly cleared (user is removing item from box)
        if not container_id_cleared:
            asset_type_lower = (asset.asset_type or '').lower()
            is_cable = (
                'cable' in asset_type_lower or
                asset_type_lower in ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
            )
            if is_cable:
                try:
                    from app.services.stock_service import sync_storage_box_for_cable
                    sync_storage_box_for_cable(self.db, asset)
                except Exception as e:
                    # Log but don't fail asset update if box sync fails
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync storage box for cable {asset.asset_tag} (ID: {asset.id}): {str(e)}")

        # Log status change
        if asset_update.status and asset_update.status != old_status:
            event = AssetLifecycleEvent(
                asset_id=asset.id,
                event_type="status_changed",
                event_timestamp=datetime.utcnow(),
                old_status=old_status.value if old_status else None,
                new_status=asset.status.value,
                notes=f"Status changed from {old_status} to {asset.status}"
            )
            self.db.add(event)
            self.db.commit()

        return asset

    def upload_photo(self, asset_id: int, file: UploadFile) -> dict:
        """
        Upload photo for asset to MinIO or local storage.
        
        Photos are stored in object storage (MinIO) or local filesystem,
        and the storage URL is saved in the asset's photo_urls array.
        """
        from app.services.storage_service import get_storage_service
        from app.core.tenant import get_current_tenant_id
        
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Read file data
        file_data = file.file.read()
        
        # Validate file size
        if len(file_data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] or ".jpg"
        unique_filename = f"assets/{asset.asset_tag}_{uuid.uuid4()}{file_extension}"
        
        # Get content type
        content_type = file.content_type or "image/jpeg"
        
        # Upload to storage (MinIO or local)
        storage_service = get_storage_service()
        tenant_id = get_current_tenant_id()
        photo_url = storage_service.upload_file(
            file_data=file_data,
            file_path=unique_filename,
            content_type=content_type,
            tenant_id=tenant_id
        )

        # Add to asset's photo URLs
        if not asset.photo_urls:
            asset.photo_urls = []

        asset.photo_urls.append(photo_url)
        asset.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(asset)

        return {
            "message": "Photo uploaded successfully",
            "photo_url": photo_url,
            "asset_id": asset_id
        }

    def deploy_asset(self, asset_id: int, rack_id: int, u_position_start: int) -> Asset:
        """Deploy asset to rack location"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Check if rack exists
        from app.models.location import Rack
        rack = self.db.query(Rack).filter(Rack.id == rack_id).first()
        if not rack:
            raise HTTPException(status_code=404, detail="Rack not found")

        # TODO: Check if position is available

        old_location = f"Rack {asset.rack_id} U{asset.rack_position_start}" if asset.rack_id else "Not deployed"

        # Update asset
        asset.rack_id = rack_id
        asset.rack_position_start = u_position_start
        asset.rack_position_end = u_position_start + (asset.height_u or 1) - 1
        asset.status = AssetStatus.DEPLOYED
        asset.deployed_at = datetime.utcnow()
        asset.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(asset)

        # Log deployment
        event = AssetLifecycleEvent(
            asset_id=asset.id,
            event_type="deployed",
            event_timestamp=datetime.utcnow(),
            old_location=old_location,
            new_location=f"Rack {rack_id} U{u_position_start}",
            old_status=AssetStatus.STAGING.value,
            new_status=AssetStatus.DEPLOYED.value,
            notes=f"Asset deployed to {rack.code} at U{u_position_start}"
        )
        self.db.add(event)
        self.db.commit()

        return asset

    def decommission_asset(self, asset_id: int, reason: str = None) -> Asset:
        """Decommission an asset"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        old_status = asset.status
        old_location = f"Rack {asset.rack_id} U{asset.rack_position_start}" if asset.rack_id else "Unknown"

        # Update asset
        asset.status = AssetStatus.DECOMMISSIONED
        asset.decommissioned_at = datetime.utcnow()
        asset.updated_at = datetime.utcnow()

        # Clear rack location
        asset.rack_id = None
        asset.rack_position_start = None
        asset.rack_position_end = None

        self.db.commit()
        self.db.refresh(asset)

        # Log decommission
        event = AssetLifecycleEvent(
            asset_id=asset.id,
            event_type="decommissioned",
            event_timestamp=datetime.utcnow(),
            old_status=old_status.value,
            new_status=AssetStatus.DECOMMISSIONED.value,
            old_location=old_location,
            new_location="Decommissioned",
            notes=reason or "Asset decommissioned"
        )
        self.db.add(event)
        self.db.commit()

        return asset
