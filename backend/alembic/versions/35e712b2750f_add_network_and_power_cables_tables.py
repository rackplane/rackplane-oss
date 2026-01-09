"""add_network_and_power_cables_tables

Revision ID: 35e712b2750f
Revises: add_original_serial_number
Create Date: 2025-11-30 07:34:49.660179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '35e712b2750f'
down_revision: Union[str, None] = 'add_original_serial_number'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create network_cables and power_cables tables if they don't exist"""
    # Use raw SQL to avoid any issues with Alembic's table creation
    conn = op.get_bind()
    
    # Check if tables exist
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('power_cables', 'network_cables')
    """))
    existing_tables = {row[0] for row in result}
    
    # Note: Models use lowercase enum values, but database has uppercase enum values from old migrations
    # We'll use VARCHAR to avoid enum mismatch issues - the models will handle validation
    from alembic import util
    # Create power_cables table if it doesn't exist
    if 'power_cables' not in existing_tables:
        util.status("Creating power_cables table...")
        try:
            op.create_table(
            'power_cables',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('connector_end_a', sa.String(length=50), nullable=False),  # Using VARCHAR instead of ENUM
            sa.Column('connector_end_b', sa.String(length=50), nullable=False),  # Using VARCHAR instead of ENUM
            sa.Column('length_meters', sa.Float(), nullable=True),
            sa.Column('voltage', sa.String(length=20), nullable=False),
            sa.Column('amperage', sa.String(length=20), nullable=True),
            sa.Column('wire_gauge', sa.String(length=20), nullable=True),
            sa.Column('color', sa.String(length=50), nullable=True),
            sa.Column('storage_container_id', sa.Integer(), nullable=True),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('model', sa.String(length=200), nullable=True),
            sa.Column('part_number', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['storage_container_id'], ['storage_containers.id'], name='power_cables_storage_container_id_fkey'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_power_cables_tenant_id'),
            sa.PrimaryKeyConstraint('id', name='power_cables_pkey')
            )
            op.create_index('ix_power_cables_id', 'power_cables', ['id'], unique=False)
            op.create_index('ix_power_cables_name', 'power_cables', ['name'], unique=False)
            op.create_index('ix_power_cables_manufacturer', 'power_cables', ['manufacturer'], unique=False)
            op.create_index('ix_power_cables_voltage', 'power_cables', ['voltage'], unique=False)
            op.create_index('ix_power_cables_connector_end_a', 'power_cables', ['connector_end_a'], unique=False)
            op.create_index('ix_power_cables_connector_end_b', 'power_cables', ['connector_end_b'], unique=False)
            op.create_index('ix_power_cables_tenant_id', 'power_cables', ['tenant_id'], unique=False)
        except Exception as e:
            util.status(f"Failed to create power_cables table: {e}")
            raise
    
    # Create network_cables table if it doesn't exist
    if 'network_cables' not in existing_tables:
        util.status("Creating network_cables table...")
        try:
            op.create_table(
            'network_cables',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('cable_type', sa.String(length=50), nullable=False),  # Using VARCHAR instead of ENUM
            sa.Column('connector_type', sa.String(length=50), nullable=False),  # Using VARCHAR instead of ENUM
            sa.Column('speed', sa.String(length=20), nullable=False),
            sa.Column('length_meters', sa.Float(), nullable=True),
            sa.Column('breakout', sa.String(length=50), nullable=True),
            sa.Column('fiber_mode', sa.String(length=20), nullable=True),
            sa.Column('wavelength', sa.String(length=20), nullable=True),
            sa.Column('storage_container_id', sa.Integer(), nullable=True),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('model', sa.String(length=200), nullable=True),
            sa.Column('serial_number', sa.String(length=200), nullable=True),
            sa.Column('part_number', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('connector_type_end_a', sa.String(length=50), nullable=True),
            sa.Column('connector_type_end_b', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['storage_container_id'], ['storage_containers.id'], name='network_cables_storage_container_id_fkey'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_network_cables_tenant_id'),
            sa.PrimaryKeyConstraint('id', name='network_cables_pkey')
            )
            op.create_index('ix_network_cables_id', 'network_cables', ['id'], unique=False)
            op.create_index('ix_network_cables_name', 'network_cables', ['name'], unique=False)
            op.create_index('ix_network_cables_manufacturer', 'network_cables', ['manufacturer'], unique=False)
            op.create_index('ix_network_cables_serial_number', 'network_cables', ['serial_number'], unique=False)
            op.create_index('ix_network_cables_speed', 'network_cables', ['speed'], unique=False)
            op.create_index('ix_network_cables_cable_type', 'network_cables', ['cable_type'], unique=False)
            op.create_index('ix_network_cables_connector_type', 'network_cables', ['connector_type'], unique=False)
            op.create_index('ix_network_cables_connector_type_end_a', 'network_cables', ['connector_type_end_a'], unique=False)
            op.create_index('ix_network_cables_connector_type_end_b', 'network_cables', ['connector_type_end_b'], unique=False)
            op.create_index('ix_network_cables_tenant_id', 'network_cables', ['tenant_id'], unique=False)
            # Create composite unique index for serial_number + tenant_id
            op.create_index('idx_network_cables_serial_tenant', 'network_cables', 
                           ['serial_number', 'tenant_id'], unique=True,
                           postgresql_where=sa.text('serial_number IS NOT NULL'))
        except Exception as e:
            util.status(f"Failed to create network_cables table: {e}")
            raise


def downgrade() -> None:
    """Drop network_cables and power_cables tables"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'network_cables' in tables:
        op.drop_index('idx_network_cables_serial_tenant', table_name='network_cables')
        op.drop_index('ix_network_cables_tenant_id', table_name='network_cables')
        op.drop_index('ix_network_cables_connector_type', table_name='network_cables')
        op.drop_index('ix_network_cables_cable_type', table_name='network_cables')
        op.drop_index('ix_network_cables_speed', table_name='network_cables')
        op.drop_index('ix_network_cables_serial_number', table_name='network_cables')
        op.drop_index('ix_network_cables_manufacturer', table_name='network_cables')
        op.drop_index('ix_network_cables_name', table_name='network_cables')
        op.drop_index('ix_network_cables_id', table_name='network_cables')
        op.drop_table('network_cables')
    
    if 'power_cables' in tables:
        op.drop_index('ix_power_cables_tenant_id', table_name='power_cables')
        op.drop_index('ix_power_cables_connector_end_b', table_name='power_cables')
        op.drop_index('ix_power_cables_connector_end_a', table_name='power_cables')
        op.drop_index('ix_power_cables_voltage', table_name='power_cables')
        op.drop_index('ix_power_cables_manufacturer', table_name='power_cables')
        op.drop_index('ix_power_cables_name', table_name='power_cables')
        op.drop_index('ix_power_cables_id', table_name='power_cables')
        op.drop_table('power_cables')
