"""add_cascade_delete_to_connections

Revision ID: cff3b4de952b
Revises: 3e2854c5c0eb
Create Date: 2025-11-21 19:53:56.713222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cff3b4de952b'
down_revision: Union[str, None] = '3e2854c5c0eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Helper function to safely drop index (handles constraint-backed indexes)
    def drop_index_if_exists(index_name, table_name, **kwargs):
        if table_name in inspector.get_table_names():
            # First check if this is actually a unique constraint (not just an index)
            # Unique constraints create backing indexes with the same name
            result = connection.execute(sa.text("""
                SELECT 1 FROM pg_constraint 
                WHERE conname = :name AND contype = 'u'
            """), {"name": index_name})
            if result.fetchone() is not None:
                # It's a constraint - drop as constraint
                op.drop_constraint(index_name, table_name, type_='unique')
                return
            
            # Otherwise check if it's a plain index
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name, **kwargs)
    
    # Helper function to safely create index
    def create_index_if_not_exists(index_name, table_name, columns, unique=False, **kwargs):
        if table_name in inspector.get_table_names():
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            if index_name not in indexes:
                op.create_index(index_name, table_name, columns, unique=unique, **kwargs)
    
    # Helper function to safely drop constraint
    def drop_constraint_if_exists(constraint_name, table_name, constraint_type='foreignkey'):
        if table_name in inspector.get_table_names():
            constraints = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
            if constraint_name in constraints:
                op.drop_constraint(constraint_name, table_name, type_=constraint_type)
    
    # Helper function to safely create foreign key
    def create_foreign_key_if_not_exists(fk_name, table_name, referred_table, local_cols, referred_cols, ondelete=None):
        if table_name in inspector.get_table_names():
            constraints = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
            if fk_name not in constraints:
                op.create_foreign_key(fk_name, table_name, referred_table, local_cols, referred_cols, ondelete=ondelete)
    
    # Drop network_cables table and indexes (if they exist)
    if 'network_cables' in inspector.get_table_names():
        drop_index_if_exists('idx_network_cables_serial_tenant', 'network_cables')
        drop_index_if_exists('ix_network_cables_cable_type', 'network_cables')
        drop_index_if_exists('ix_network_cables_connector_type', 'network_cables')
        drop_index_if_exists('ix_network_cables_id', 'network_cables')
        drop_index_if_exists('ix_network_cables_manufacturer', 'network_cables')
        drop_index_if_exists('ix_network_cables_name', 'network_cables')
        drop_index_if_exists('ix_network_cables_serial_number', 'network_cables')
        drop_index_if_exists('ix_network_cables_speed', 'network_cables')
        drop_index_if_exists('ix_network_cables_tenant_id', 'network_cables')
        op.drop_table('network_cables')
    
    # Drop power_cables table and indexes (if they exist)
    if 'power_cables' in inspector.get_table_names():
        drop_index_if_exists('ix_power_cables_connector_end_a', 'power_cables')
        drop_index_if_exists('ix_power_cables_connector_end_b', 'power_cables')
        drop_index_if_exists('ix_power_cables_id', 'power_cables')
        drop_index_if_exists('ix_power_cables_manufacturer', 'power_cables')
        drop_index_if_exists('ix_power_cables_name', 'power_cables')
        drop_index_if_exists('ix_power_cables_tenant_id', 'power_cables')
        drop_index_if_exists('ix_power_cables_voltage', 'power_cables')
        op.drop_table('power_cables')
    
    # Update asset_types indexes
    if 'asset_types' in inspector.get_table_names():
        drop_index_if_exists('idx_asset_types_name_tenant', 'asset_types')
        create_index_if_not_exists('ix_asset_types_name', 'asset_types', ['name'], unique=False)
    
    # Update assets indexes
    if 'assets' in inspector.get_table_names():
        drop_index_if_exists('idx_assets_hostname_tenant', 'assets')
        drop_index_if_exists('idx_assets_serial_tenant', 'assets')
        drop_index_if_exists('idx_assets_tag_tenant', 'assets')
        drop_index_if_exists('ix_assets_container_id', 'assets')
        drop_index_if_exists('ix_assets_asset_tag', 'assets')
        create_index_if_not_exists('ix_assets_asset_tag', 'assets', ['asset_tag'], unique=False)
        drop_index_if_exists('ix_assets_serial_number', 'assets')
        create_index_if_not_exists('ix_assets_serial_number', 'assets', ['serial_number'], unique=False)
    
    # Update connections foreign keys
    if 'connections' in inspector.get_table_names():
        # Drop old foreign keys if they exist, then recreate with CASCADE
        drop_constraint_if_exists('connections_cable_asset_id_fkey', 'connections')
        drop_constraint_if_exists('connections_device_asset_id_fkey', 'connections')
        # Create new ones with CASCADE
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'connections_device_asset_id_fkey'
                    AND contype = 'f'
                ) THEN
                    ALTER TABLE connections 
                    ADD CONSTRAINT connections_device_asset_id_fkey 
                    FOREIGN KEY (device_asset_id) REFERENCES assets(id) ON DELETE CASCADE;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'connections_cable_asset_id_fkey'
                    AND contype = 'f'
                ) THEN
                    ALTER TABLE connections 
                    ADD CONSTRAINT connections_cable_asset_id_fkey 
                    FOREIGN KEY (cable_asset_id) REFERENCES assets(id) ON DELETE CASCADE;
                END IF;
            END $$;
        """)
    
    # Update datacenters indexes
    if 'datacenters' in inspector.get_table_names():
        drop_index_if_exists('idx_datacenters_code_tenant', 'datacenters')
        drop_index_if_exists('idx_datacenters_name_tenant', 'datacenters')
        drop_index_if_exists('ix_datacenters_name', 'datacenters')
        create_index_if_not_exists('ix_datacenters_name', 'datacenters', ['name'], unique=False)
    
    # Update environmental_sensors indexes
    if 'environmental_sensors' in inspector.get_table_names():
        drop_index_if_exists('idx_environmental_sensors_sensor_id_tenant', 'environmental_sensors')
        drop_index_if_exists('ix_environmental_sensors_sensor_id', 'environmental_sensors')
        create_index_if_not_exists('ix_environmental_sensors_sensor_id', 'environmental_sensors', ['sensor_id'], unique=False)
    
    # Update racks indexes
    if 'racks' in inspector.get_table_names():
        drop_index_if_exists('idx_racks_code_tenant', 'racks')
    
    # Update storage_containers indexes
    if 'storage_containers' in inspector.get_table_names():
        drop_index_if_exists('idx_storage_containers_barcode_tenant', 'storage_containers')
        drop_index_if_exists('idx_storage_containers_name_tenant', 'storage_containers')
        drop_index_if_exists('ix_storage_containers_barcode', 'storage_containers')
        create_index_if_not_exists('ix_storage_containers_barcode', 'storage_containers', ['barcode'], unique=False)
        drop_index_if_exists('ix_storage_containers_name', 'storage_containers')
        create_index_if_not_exists('ix_storage_containers_name', 'storage_containers', ['name'], unique=False)
    
    # Update users indexes
    if 'users' in inspector.get_table_names():
        drop_index_if_exists('idx_users_username_tenant', 'users')
        drop_index_if_exists('ix_users_username', 'users')
        create_index_if_not_exists('ix_users_username', 'users', ['username'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('idx_users_username_tenant', 'users', ['username', 'tenant_id'], unique=True)
    op.drop_index(op.f('ix_storage_containers_name'), table_name='storage_containers')
    op.create_index('ix_storage_containers_name', 'storage_containers', ['name'], unique=True)
    op.drop_index(op.f('ix_storage_containers_barcode'), table_name='storage_containers')
    op.create_index('ix_storage_containers_barcode', 'storage_containers', ['barcode'], unique=True)
    op.create_index('idx_storage_containers_name_tenant', 'storage_containers', ['name', 'tenant_id'], unique=True)
    op.create_index('idx_storage_containers_barcode_tenant', 'storage_containers', ['barcode', 'tenant_id'], unique=True, postgresql_where='(barcode IS NOT NULL)')
    op.create_index('idx_racks_code_tenant', 'racks', ['code', 'tenant_id'], unique=True)
    op.drop_index(op.f('ix_environmental_sensors_sensor_id'), table_name='environmental_sensors')
    op.create_index('ix_environmental_sensors_sensor_id', 'environmental_sensors', ['sensor_id'], unique=True)
    op.create_index('idx_environmental_sensors_sensor_id_tenant', 'environmental_sensors', ['sensor_id', 'tenant_id'], unique=True)
    op.drop_index(op.f('ix_datacenters_name'), table_name='datacenters')
    op.create_index('ix_datacenters_name', 'datacenters', ['name'], unique=True)
    op.create_index('idx_datacenters_name_tenant', 'datacenters', ['name', 'tenant_id'], unique=True)
    op.create_index('idx_datacenters_code_tenant', 'datacenters', ['code', 'tenant_id'], unique=True)
    op.drop_constraint(None, 'connections', type_='foreignkey')
    op.drop_constraint(None, 'connections', type_='foreignkey')
    op.create_foreign_key('connections_device_asset_id_fkey', 'connections', 'assets', ['device_asset_id'], ['id'])
    op.create_foreign_key('connections_cable_asset_id_fkey', 'connections', 'assets', ['cable_asset_id'], ['id'])
    op.drop_index(op.f('ix_assets_serial_number'), table_name='assets')
    op.create_index('ix_assets_serial_number', 'assets', ['serial_number'], unique=True)
    op.drop_index(op.f('ix_assets_asset_tag'), table_name='assets')
    op.create_index('ix_assets_asset_tag', 'assets', ['asset_tag'], unique=True)
    op.create_index('ix_assets_container_id', 'assets', ['container_id'], unique=False)
    op.create_index('idx_assets_tag_tenant', 'assets', ['asset_tag', 'tenant_id'], unique=True)
    op.create_index('idx_assets_serial_tenant', 'assets', ['serial_number', 'tenant_id'], unique=True)
    op.create_index('idx_assets_hostname_tenant', 'assets', ['hostname', 'tenant_id'], unique=True, postgresql_where='(hostname IS NOT NULL)')
    op.drop_index(op.f('ix_asset_types_name'), table_name='asset_types')
    op.create_index('idx_asset_types_name_tenant', 'asset_types', ['name', 'tenant_id'], unique=True)
    op.create_table('power_cables',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('connector_end_a', postgresql.ENUM('C13', 'C14', 'C15', 'C19', 'C20', 'C21', 'NEMA_5_15P', 'NEMA_5_15R', 'NEMA_L5_20P', 'NEMA_L5_20R', 'NEMA_L6_20P', 'NEMA_L6_20R', 'NEMA_L6_30P', 'NEMA_L6_30R', 'CEE_7_7', 'BS_1363', name='powerconnectortype'), autoincrement=False, nullable=False),
    sa.Column('connector_end_b', postgresql.ENUM('C13', 'C14', 'C15', 'C19', 'C20', 'C21', 'NEMA_5_15P', 'NEMA_5_15R', 'NEMA_L5_20P', 'NEMA_L5_20R', 'NEMA_L6_20P', 'NEMA_L6_20R', 'NEMA_L6_30P', 'NEMA_L6_30R', 'CEE_7_7', 'BS_1363', name='powerconnectortype'), autoincrement=False, nullable=False),
    sa.Column('length_meters', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('voltage', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('amperage', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('wire_gauge', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('color', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('storage_container_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('manufacturer', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('model', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('part_number', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('tenant_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['storage_container_id'], ['storage_containers.id'], name='power_cables_storage_container_id_fkey'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_power_cables_tenant_id'),
    sa.PrimaryKeyConstraint('id', name='power_cables_pkey')
    )
    op.create_index('ix_power_cables_voltage', 'power_cables', ['voltage'], unique=False)
    op.create_index('ix_power_cables_tenant_id', 'power_cables', ['tenant_id'], unique=False)
    op.create_index('ix_power_cables_name', 'power_cables', ['name'], unique=False)
    op.create_index('ix_power_cables_manufacturer', 'power_cables', ['manufacturer'], unique=False)
    op.create_index('ix_power_cables_id', 'power_cables', ['id'], unique=False)
    op.create_index('ix_power_cables_connector_end_b', 'power_cables', ['connector_end_b'], unique=False)
    op.create_index('ix_power_cables_connector_end_a', 'power_cables', ['connector_end_a'], unique=False)
    op.create_table('network_cables',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('cable_type', postgresql.ENUM('CAT5E', 'CAT6', 'CAT6A', 'CAT7', 'FIBER_SM', 'FIBER_MM', 'DAC', 'POWER', 'OTHER', name='cabletype'), autoincrement=False, nullable=False),
    sa.Column('connector_type', postgresql.ENUM('RJ45', 'SFP', 'SFP_PLUS', 'QSFP', 'QSFP_PLUS', 'QSFP28', 'QSFP56', 'QSFP_DD', 'OSFP', 'LC', 'SC', 'MPO', name='connectortype'), autoincrement=False, nullable=False),
    sa.Column('speed', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('length_meters', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('breakout', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('fiber_mode', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('wavelength', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('storage_container_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('manufacturer', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('model', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('serial_number', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('part_number', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('tenant_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['storage_container_id'], ['storage_containers.id'], name='network_cables_storage_container_id_fkey'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_network_cables_tenant_id'),
    sa.PrimaryKeyConstraint('id', name='network_cables_pkey')
    )
    op.create_index('ix_network_cables_tenant_id', 'network_cables', ['tenant_id'], unique=False)
    op.create_index('ix_network_cables_speed', 'network_cables', ['speed'], unique=False)
    op.create_index('ix_network_cables_serial_number', 'network_cables', ['serial_number'], unique=True)
    op.create_index('ix_network_cables_name', 'network_cables', ['name'], unique=False)
    op.create_index('ix_network_cables_manufacturer', 'network_cables', ['manufacturer'], unique=False)
    op.create_index('ix_network_cables_id', 'network_cables', ['id'], unique=False)
    op.create_index('ix_network_cables_connector_type', 'network_cables', ['connector_type'], unique=False)
    op.create_index('ix_network_cables_cable_type', 'network_cables', ['cable_type'], unique=False)
    op.create_index('idx_network_cables_serial_tenant', 'network_cables', ['serial_number', 'tenant_id'], unique=True, postgresql_where='(serial_number IS NOT NULL)')
    # ### end Alembic commands ###

