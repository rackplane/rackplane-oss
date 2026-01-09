# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Location Service - Business Logic
Handles datacenter, room, rack, and capacity management
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import Optional, List

from app.models.location import Datacenter, Room, Rack
from app.models.asset import Asset
from app.schemas.location import DatacenterCreate, RoomCreate, RackCreate, RackCapacityResponse
from app.core.config import settings


class LocationService:
    def __init__(self, db: Session):
        self.db = db

    def create_datacenter(self, dc_data: DatacenterCreate) -> Datacenter:
        """Create a new datacenter"""
        from app.core.tenant_query import apply_tenant_filter
        
        # Check for duplicate name within tenant
        query = self.db.query(Datacenter).filter(Datacenter.name == dc_data.name)
        query = apply_tenant_filter(query, Datacenter)
        existing_by_name = query.first()
        if existing_by_name:
            raise HTTPException(
                status_code=400,
                detail=f"Datacenter with name '{dc_data.name}' already exists in this tenant"
            )
        
        # Check for duplicate code within tenant
        query = self.db.query(Datacenter).filter(Datacenter.code == dc_data.code)
        query = apply_tenant_filter(query, Datacenter)
        existing_by_code = query.first()
        if existing_by_code:
            raise HTTPException(
                status_code=400,
                detail=f"Datacenter with code '{dc_data.code}' already exists in this tenant"
            )
        
        dc = Datacenter(**dc_data.model_dump())
        self.db.add(dc)
        self.db.commit()
        self.db.refresh(dc)
        return dc

    def create_room(self, room_data: RoomCreate) -> Room:
        """Create a new room"""
        from app.core.tenant_query import apply_tenant_filter
        
        # Validate that datacenter exists and belongs to current tenant
        query = self.db.query(Datacenter).filter(Datacenter.id == room_data.datacenter_id)
        query = apply_tenant_filter(query, Datacenter)
        datacenter = query.first()
        if not datacenter:
            raise HTTPException(status_code=404, detail="Datacenter not found or does not belong to your tenant")
        
        room = Room(**room_data.model_dump())
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def create_rack(self, rack_data: RackCreate) -> Rack:
        """Create a new rack"""
        from app.core.tenant_query import apply_tenant_filter
        
        # Validate that datacenter exists and belongs to current tenant
        query = self.db.query(Datacenter).filter(Datacenter.id == rack_data.datacenter_id)
        query = apply_tenant_filter(query, Datacenter)
        datacenter = query.first()
        if not datacenter:
            raise HTTPException(status_code=404, detail="Datacenter not found or does not belong to your tenant")
        
        # Validate that room exists and belongs to current tenant (if provided)
        if rack_data.room_id:
            query = self.db.query(Room).filter(Room.id == rack_data.room_id)
            query = apply_tenant_filter(query, Room)
            room = query.first()
            if not room:
                raise HTTPException(status_code=404, detail="Room not found or does not belong to your tenant")
            # Also validate that room belongs to the same datacenter
            if room.datacenter_id != rack_data.datacenter_id:
                raise HTTPException(status_code=400, detail="Room does not belong to the specified datacenter")
        
        # Check for duplicate rack code within tenant (should be unique per tenant)
        query = self.db.query(Rack).filter(Rack.code == rack_data.code)
        query = apply_tenant_filter(query, Rack)
        existing_rack = query.first()
        if existing_rack:
            raise HTTPException(
                status_code=400,
                detail=f"Rack with code '{rack_data.code}' already exists in this tenant"
            )
        
        # Also check for duplicate name within tenant (optional, but good practice)
        query = self.db.query(Rack).filter(Rack.name == rack_data.name)
        query = apply_tenant_filter(query, Rack)
        existing_rack_by_name = query.first()
        if existing_rack_by_name:
            raise HTTPException(
                status_code=400,
                detail=f"Rack with name '{rack_data.name}' already exists in this tenant"
            )
        
        rack = Rack(**rack_data.model_dump())
        self.db.add(rack)
        self.db.commit()
        self.db.refresh(rack)
        return rack

    def get_rack_capacity(self, rack_id: int) -> RackCapacityResponse:
        """Calculate rack capacity metrics"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Rack).filter(Rack.id == rack_id)
        query = apply_tenant_filter(query, Rack)
        rack = query.first()
        if not rack:
            raise HTTPException(status_code=404, detail="Rack not found")

        # Get assets in rack
        query = self.db.query(Asset).filter(Asset.rack_id == rack_id)
        query = apply_tenant_filter(query, Asset)
        assets = query.all()

        # Calculate U-space utilization
        total_u = rack.height_u
        used_u = sum(asset.height_u or 1 for asset in assets)
        available_u = total_u - used_u
        u_utilization = (used_u / total_u * 100) if total_u > 0 else 0

        # Calculate power utilization
        total_power = rack.power_capacity_watts or 0
        used_power = sum(asset.power_consumption_watts or 0 for asset in assets)
        available_power = total_power - used_power
        power_utilization = (used_power / total_power * 100) if total_power > 0 else 0

        # Check warnings
        space_warning = u_utilization >= (settings.RACK_SPACE_WARNING_THRESHOLD * 100)
        power_warning = power_utilization >= (settings.POWER_WARNING_THRESHOLD * 100)

        return RackCapacityResponse(
            rack_id=rack.id,
            rack_code=rack.code,
            total_u_space=total_u,
            used_u_space=used_u,
            available_u_space=available_u,
            u_space_utilization_percent=round(u_utilization, 2),
            total_power_capacity_watts=total_power,
            used_power_watts=round(used_power, 2),
            available_power_watts=round(available_power, 2),
            power_utilization_percent=round(power_utilization, 2),
            space_warning=space_warning,
            power_warning=power_warning
        )

    def get_available_positions(self, rack_id: int, u_height: int) -> List[int]:
        """Find available U positions for a device of specified height"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Rack).filter(Rack.id == rack_id)
        query = apply_tenant_filter(query, Rack)
        rack = query.first()
        if not rack:
            raise HTTPException(status_code=404, detail="Rack not found")

        # Get all assets in rack
        query = self.db.query(Asset).filter(Asset.rack_id == rack_id)
        query = apply_tenant_filter(query, Asset)
        assets = query.order_by(Asset.rack_position_start).all()

        # Create occupied positions set
        occupied = set()
        for asset in assets:
            start = asset.rack_position_start or 0
            end = asset.rack_position_end or start
            for pos in range(start, end + 1):
                occupied.add(pos)

        # Find available contiguous positions
        available_positions = []
        for start_pos in range(1, rack.height_u - u_height + 2):
            # Check if all positions from start_pos to start_pos+u_height-1 are free
            if all(pos not in occupied for pos in range(start_pos, start_pos + u_height)):
                available_positions.append(start_pos)

        return available_positions

    def get_rack_visual(self, rack_id: int) -> dict:
        """Generate visual representation of rack"""
        from app.core.tenant_query import apply_tenant_filter
        
        query = self.db.query(Rack).filter(Rack.id == rack_id)
        query = apply_tenant_filter(query, Rack)
        rack = query.first()
        if not rack:
            raise HTTPException(status_code=404, detail="Rack not found")

        # Get all assets
        query = self.db.query(Asset).filter(Asset.rack_id == rack_id)
        query = apply_tenant_filter(query, Asset)
        assets = query.all()

        # Create U position map
        u_map = {}
        for u in range(1, rack.height_u + 1):
            u_map[u] = {"occupied": False, "asset": None}

        for asset in assets:
            if asset.rack_position_start:
                for u in range(asset.rack_position_start, (asset.rack_position_end or asset.rack_position_start) + 1):
                    u_map[u] = {
                        "occupied": True,
                        "asset": {
                            "id": asset.id,
                            "asset_tag": asset.asset_tag,
                            "model": f"{asset.manufacturer} {asset.model}",
                            "height_u": asset.height_u,
                            "power_watts": asset.power_consumption_watts
                        }
                    }

        return {
            "rack_id": rack.id,
            "rack_code": rack.code,
            "total_u": rack.height_u,
            "u_map": u_map
        }

    def suggest_placement(self, rack_id: int, u_height: int, power_watts: float) -> dict:
        """Suggest optimal U position for new asset"""
        available = self.get_available_positions(rack_id, u_height)

        if not available:
            return {"available": False, "message": "No available positions in rack"}

        # Get rack capacity
        capacity = self.get_rack_capacity(rack_id)

        # Check power capacity
        if capacity.available_power_watts < power_watts:
            return {
                "available": False,
                "message": "Insufficient power capacity",
                "power_needed": power_watts,
                "power_available": capacity.available_power_watts
            }

        # Suggest bottom-most position (standard practice)
        suggested_position = min(available)

        return {
            "available": True,
            "suggested_u_position": suggested_position,
            "alternative_positions": available[:5],  # Top 5 alternatives
            "total_available_positions": len(available)
        }

    def find_optimal_rack(
        self,
        datacenter_id: int,
        u_height: int,
        power_watts: float,
        cooling_btu: Optional[float] = None,
        prioritize: str = "power_efficiency"
    ) -> dict:
        """Find optimal rack for new asset based on capacity"""
        from app.core.tenant_query import apply_tenant_filter
        
        # Get all racks in datacenter
        query = self.db.query(Rack).filter(
            Rack.datacenter_id == datacenter_id,
            Rack.is_active == True
        )
        query = apply_tenant_filter(query, Rack)
        racks = query.all()

        suitable_racks = []

        for rack in racks:
            # Check if rack has available space
            available_positions = self.get_available_positions(rack.id, u_height)
            if not available_positions:
                continue

            # Check capacity
            capacity = self.get_rack_capacity(rack.id)

            # Check power
            if capacity.available_power_watts < power_watts:
                continue

            # Calculate efficiency score
            if prioritize == "power_efficiency":
                # Prefer racks with moderate utilization (avoid hot spots but maximize usage)
                target_utilization = 70
                score = 100 - abs(capacity.power_utilization_percent - target_utilization)
            elif prioritize == "space":
                # Prefer racks with most available space
                score = capacity.available_u_space
            else:  # balanced
                space_score = capacity.available_u_space / capacity.total_u_space * 50
                power_score = (100 - capacity.power_utilization_percent) * 0.5
                score = space_score + power_score

            suitable_racks.append({
                "rack": rack,
                "capacity": capacity,
                "score": score,
                "suggested_position": min(available_positions),
                "available_positions_count": len(available_positions)
            })

        if not suitable_racks:
            return {
                "found": False,
                "message": "No suitable racks found with required capacity"
            }

        # Sort by score
        suitable_racks.sort(key=lambda x: x["score"], reverse=True)

        best_rack = suitable_racks[0]

        return {
            "found": True,
            "recommended_rack": {
                "rack_id": best_rack["rack"].id,
                "rack_code": best_rack["rack"].code,
                "suggested_u_position": best_rack["suggested_position"],
                "available_positions": best_rack["available_positions_count"],
                "current_power_utilization": best_rack["capacity"].power_utilization_percent,
                "current_space_utilization": best_rack["capacity"].u_space_utilization_percent
            },
            "alternatives": [
                {
                    "rack_id": alt["rack"].id,
                    "rack_code": alt["rack"].code,
                    "score": alt["score"]
                }
                for alt in suitable_racks[1:4]  # Top 3 alternatives
            ]
        }
