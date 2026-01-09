"""auto_create_storage_boxes_for_cables

Revision ID: f1bb2a847c92
Revises: 2f5ac940c23e
Create Date: 2025-11-22 01:25:56.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'f1bb2a847c92'
down_revision: Union[str, None] = '2f5ac940c23e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def normalize_length(length_str: str) -> str:
    """Normalize length string (e.g., '1m' -> '1M', '3 feet' -> '3FT')"""
    if not length_str:
        return ''
    normalized = str(length_str).strip().upper().replace(' ', '')
    if normalized.endswith('m') and not normalized.endswith('M'):
        normalized = normalized[:-1] + 'M'
    elif normalized.endswith('ft') and not normalized.endswith('FT'):
        normalized = normalized[:-2] + 'FT'
    return normalized


def generate_box_name(asset_type: str, custom_fields: dict) -> str:
    """Generate storage box name from cable specifications"""
    if asset_type == 'dac_cable':
        speed = custom_fields.get('dac_speed', '').strip().upper() if custom_fields.get('dac_speed') else ''
        connector_a = custom_fields.get('dac_connector_a', '').strip().upper() if custom_fields.get('dac_connector_a') else ''
        connector_b = custom_fields.get('dac_connector_b', '').strip().upper() if custom_fields.get('dac_connector_b') else ''
        length = normalize_length(custom_fields.get('cable_length', '')) if custom_fields.get('cable_length') else ''
        
        if speed and connector_a and connector_b:
            if not length:
                length = 'VAR'
            return f"DAC-{speed}-{connector_a}-{connector_b}-{length}"
    
    elif asset_type == 'fiber_cable':
        fiber_type = custom_fields.get('fiber_type', '').strip().upper() if custom_fields.get('fiber_type') else ''
        connector_a = custom_fields.get('fiber_connector_a', '').strip().upper() if custom_fields.get('fiber_connector_a') else ''
        connector_b = custom_fields.get('fiber_connector_b', '').strip().upper() if custom_fields.get('fiber_connector_b') else ''
        length = normalize_length(custom_fields.get('cable_length', '')) if custom_fields.get('cable_length') else ''
        
        if fiber_type and connector_a and connector_b:
            if not length:
                length = 'VAR'
            return f"FIBER-{fiber_type}-{connector_a}-{connector_b}-{length}"
    
    return None


def upgrade() -> None:
    """
    Automatically create storage boxes for cables that are in storage.
    For each unique cable type (based on box name generation), create or update
    the storage box and set min_stock_threshold to the number of cables of that type.
    """
    connection = op.get_bind()
    
    # Get all cables that are in storage (have container_id set or status = 'in_storage')
    # We'll process them by tenant to respect multi-tenancy
    tenants_result = connection.execute(text("SELECT id FROM tenants"))
    tenants = [row[0] for row in tenants_result]
    
    for tenant_id in tenants:
        # Get all cables for this tenant
        cables_result = connection.execute(text("""
            SELECT id, asset_tag, asset_type, custom_fields, tenant_id
            FROM assets
            WHERE tenant_id = :tenant_id
            AND (
                asset_type ILIKE '%cable%'
                OR asset_type IN ('dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable')
            )
        """), {"tenant_id": tenant_id})
        
        cables = cables_result.fetchall()
        
        # Group cables by their box name
        from collections import defaultdict
        import json
        
        cable_groups = defaultdict(list)
        
        for cable in cables:
            cable_id, asset_tag, asset_type, custom_fields_json, cable_tenant_id = cable
            
            # Parse custom_fields JSON
            try:
                if isinstance(custom_fields_json, str):
                    custom_fields = json.loads(custom_fields_json) if custom_fields_json else {}
                else:
                    custom_fields = custom_fields_json or {}
            except:
                custom_fields = {}
            
            # Generate box name
            box_name = generate_box_name(asset_type, custom_fields)
            
            if box_name:
                cable_groups[box_name].append(cable_id)
        
        # For each unique box name, create or update the storage box
        for box_name, cable_ids in cable_groups.items():
            cable_count = len(cable_ids)
            
            # Check if box already exists
            existing_box = connection.execute(text("""
                SELECT id, min_stock_threshold
                FROM assets
                WHERE tenant_id = :tenant_id
                AND asset_tag = :box_name
            """), {"tenant_id": tenant_id, "box_name": box_name}).fetchone()
            
            if existing_box:
                box_id, current_threshold = existing_box
                # Update threshold to match cable count (at least 1)
                new_threshold = max(cable_count, 1)
                if current_threshold != new_threshold:
                    connection.execute(text("""
                        UPDATE assets
                        SET min_stock_threshold = :threshold
                        WHERE id = :box_id
                    """), {"threshold": new_threshold, "box_id": box_id})
            else:
                # Create new storage box
                # Get a default status - use 'active' for storage boxes
                connection.execute(text("""
                    INSERT INTO assets (
                        asset_tag, serial_number, asset_type, manufacturer, model,
                        status, min_stock_threshold, description, tenant_id, created_at, updated_at
                    ) VALUES (
                        :asset_tag, :serial_number, 'storage_box', 'System', 'Storage Box',
                        'active', :threshold, :description, :tenant_id, NOW(), NOW()
                    )
                """), {
                    "asset_tag": box_name,
                    "serial_number": f"{box_name}-BOX",
                    "threshold": max(cable_count, 1),
                    "description": f"Auto-generated storage box for {box_name} cables (min threshold: {max(cable_count, 1)})",
                    "tenant_id": tenant_id
                })


def downgrade() -> None:
    """
    Downgrade: Cannot automatically remove boxes that were created.
    This is a one-way migration.
    """
    pass
