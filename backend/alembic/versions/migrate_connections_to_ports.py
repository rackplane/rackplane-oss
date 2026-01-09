# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""migrate connections to port-based model

Revision ID: migrate_connections_to_ports
Revises: add_port_templates
Create Date: 2025-12-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

# revision identifiers, used by Alembic.
revision = 'migrate_connections_to_ports'
down_revision = 'add_service_contracts'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate connections from device_asset_id + port_label to port_id.
    
    Steps:
    1. Add port_id column (nullable during migration)
    2. Migrate data: link existing connections to ports (create ports if needed)
    3. Make port_id NOT NULL
    4. Make device_asset_id nullable (deprecated but kept for safety)
    5. Drop port_label column
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Check if port_id column already exists (idempotency)
    columns = [col['name'] for col in inspector.get_columns('connections')]
    
    if 'port_id' not in columns:
        # Step 1: Add new port_id column (nullable during migration)
        op.add_column('connections', sa.Column('port_id', sa.Integer(), nullable=True))
        
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_connections_port',
            'connections', 'network_ports',
            ['port_id'], ['id'],
            ondelete='CASCADE'
        )
        
        # Add index for performance
        op.create_index('idx_connections_port', 'connections', ['port_id'])
        
        print("✓ Added port_id column to connections table")
    
    # Step 2: Migrate data
    session = Session(bind=bind)
    migrate_connections_data(session)
    session.close()
    
    # Step 3: After data migration, verify all connections have port_id
    result = bind.execute(text("SELECT COUNT(*) FROM connections WHERE port_id IS NULL"))
    null_count = result.scalar()
    
    if null_count > 0:
        print(f"⚠ WARNING: {null_count} connections still have NULL port_id")
        # Don't proceed with making column NOT NULL if there are still nulls
        return
    
    # Step 4: Make port_id NOT NULL (if all connections migrated)
    # First check if column is already NOT NULL
    col_info = [col for col in inspector.get_columns('connections') if col['name'] == 'port_id']
    if col_info and col_info[0].get('nullable', True):
        op.alter_column('connections', 'port_id', nullable=False)
        print("✓ Made port_id NOT NULL")
    
    # Step 5: Make device_asset_id nullable (keep for now, can drop later)
    col_info = [col for col in inspector.get_columns('connections') if col['name'] == 'device_asset_id']
    if col_info and not col_info[0].get('nullable', True):
        op.alter_column('connections', 'device_asset_id', nullable=True)
        print("✓ Made device_asset_id nullable (deprecated)")
    
    # Step 6: Drop port_label column (no longer needed)
    if 'port_label' in columns:
        op.drop_column('connections', 'port_label')
        print("✓ Dropped port_label column")
    
    print("✓ Connection migration complete")


def downgrade():
    """
    Restore old schema.
    Note: This only restores structure, not data.
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('connections')]
    
    # Restore port_label column
    if 'port_label' not in columns:
        op.add_column('connections', sa.Column('port_label', sa.String(100), nullable=True))
    
    # Make device_asset_id NOT NULL again
    col_info = [col for col in inspector.get_columns('connections') if col['name'] == 'device_asset_id']
    if col_info and col_info[0].get('nullable', True):
        op.alter_column('connections', 'device_asset_id', nullable=False)
    
    # Drop port_id column
    if 'port_id' in columns:
        op.drop_constraint('fk_connections_port', 'connections', type_='foreignkey')
        op.drop_index('idx_connections_port', table_name='connections')
        op.drop_column('connections', 'port_id')


def migrate_connections_data(session: Session):
    """
    Migrate existing connections to port-based model.
    
    For each connection:
    1. Find existing NetworkPort for the device
    2. If not found, create a new NetworkPort
    3. Set connection.port_id = port.id
    
    Note: port_label column may not exist in all databases, so we don't rely on it.
    Instead we use end_label and device info to create sensible port names.
    """
    # Check if port_label column exists
    inspector = inspect(session.bind)
    columns = [col['name'] for col in inspector.get_columns('connections')]
    has_port_label = 'port_label' in columns
    
    # Get all connections that need migration (port_id is NULL)
    if has_port_label:
        query = """
            SELECT c.id, c.cable_asset_id, c.device_asset_id, c.port_label, c.end_label, c.tenant_id,
                   a.asset_tag, a.manufacturer, a.model
            FROM connections c
            LEFT JOIN assets a ON c.device_asset_id = a.id
            WHERE c.port_id IS NULL
        """
    else:
        # No port_label column - use NULL as placeholder
        query = """
            SELECT c.id, c.cable_asset_id, c.device_asset_id, NULL as port_label, c.end_label, c.tenant_id,
                   a.asset_tag, a.manufacturer, a.model
            FROM connections c
            LEFT JOIN assets a ON c.device_asset_id = a.id
            WHERE c.port_id IS NULL
        """
    
    connections = session.execute(text(query)).fetchall()
    
    if not connections:
        print("✓ No connections to migrate")
        return
    
    print(f"➜ Migrating {len(connections)} connections...")
    
    migrated_count = 0
    created_ports = 0
    
    for row in connections:
        conn_id = row[0]
        device_asset_id = row[2]
        port_label = row[3] if row[3] else None
        end_label = row[4] or "A"
        tenant_id = row[5]
        asset_tag = row[6] or f"Asset-{device_asset_id}"
        
        if not device_asset_id:
            print(f"  ⚠ Connection {conn_id} has no device_asset_id, skipping")
            continue
        
        # Generate port identifier if none provided
        if not port_label:
            port_label = f"Port-{end_label}"
        
        # Try to find existing port
        port_result = session.execute(
            text("""
                SELECT id FROM network_ports
                WHERE asset_id = :asset_id
                  AND tenant_id = :tenant_id
                  AND (
                    port_label = :port_label 
                    OR port_name = :port_label 
                    OR port_number = :port_label
                  )
                LIMIT 1
            """),
            {
                "asset_id": device_asset_id,
                "port_label": port_label,
                "tenant_id": tenant_id
            }
        ).fetchone()
        
        if port_result:
            port_id = port_result[0]
        else:
            # Create new port for this connection
            port_insert = session.execute(
                text("""
                    INSERT INTO network_ports (
                        asset_id, tenant_id, port_number, port_name, port_label,
                        port_type, status, enabled, created_at, updated_at
                    ) VALUES (
                        :asset_id, :tenant_id, :port_number, :port_name, :port_label,
                        'other', 'active', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    ) RETURNING id
                """),
                {
                    "asset_id": device_asset_id,
                    "tenant_id": tenant_id,
                    "port_number": port_label,
                    "port_name": f"{asset_tag}:{port_label}",
                    "port_label": port_label
                }
            )
            port_id = port_insert.fetchone()[0]
            created_ports += 1
        
        # Update connection with port_id
        session.execute(
            text("UPDATE connections SET port_id = :port_id WHERE id = :id"),
            {"port_id": port_id, "id": conn_id}
        )
        migrated_count += 1
    
    session.commit()
    
    print(f"✓ Migrated {migrated_count} connections")
    if created_ports > 0:
        print(f"✓ Created {created_ports} new ports during migration")

