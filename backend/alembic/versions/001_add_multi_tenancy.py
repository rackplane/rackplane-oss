"""Add multi-tenancy support

Revision ID: 001_add_multi_tenancy
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_multi_tenancy'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Step 1: Create tenants table (if it doesn't exist)
    if 'tenants' not in inspector.get_table_names():
        op.create_table(
            'tenants',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('slug', sa.String(length=100), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('subscription_tier', sa.String(length=50), nullable=True, server_default='standard'),
            sa.Column('contact_email', sa.String(length=200), nullable=True),
            sa.Column('contact_phone', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_tenants_id', 'tenants', ['id'], unique=False)
        op.create_index('ix_tenants_name', 'tenants', ['name'], unique=True)
        op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)
    
    # Step 2: Create default tenant and get its ID (if it doesn't exist)
    # Check for existing admin tenant (created by bootstrap) or default tenant
    result = connection.execute(sa.text("""
        SELECT id FROM tenants WHERE id = 1 OR slug IN ('default', 'admin')
    """))
    default_tenant = result.fetchone()

    if default_tenant is None:
        result = connection.execute(sa.text("""
            INSERT INTO tenants (id, name, slug, is_active, subscription_tier)
            VALUES (1, 'Default Tenant', 'default', true, 'standard')
            RETURNING id
        """))
        default_tenant_id = result.scalar()
    else:
        default_tenant_id = default_tenant[0]
    
    # Step 3: Add tenant_id columns to all tables (nullable first)
    tables_with_tenant = [
        'users',
        'assets',
        'asset_lifecycle_events',
        'asset_types',
        'datacenters',
        'rooms',
        'racks',
        'rack_positions',
        'storage_containers',
        'maintenance_records',
        'maintenance_predictions',
        'workflows',
        'workflow_executions',
        'workflow_steps',
        'environmental_sensors',
        'environmental_readings',
        'network_ports',
        'network_connections',
        'vlans',
        'capacity_metrics',
        'power_metrics',
        'cooling_metrics',
        'network_cables',
        'power_cables',
    ]
    
    for table_name in tables_with_tenant:
        # Check if table exists before adding column
        if table_name in inspector.get_table_names():
            # Check if column already exists
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            if 'tenant_id' not in columns:
                # Add tenant_id column as nullable
                op.add_column(table_name, sa.Column('tenant_id', sa.Integer(), nullable=True))
            
            # Create index if it doesn't exist
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            if f'ix_{table_name}_tenant_id' not in indexes:
                op.create_index(f'ix_{table_name}_tenant_id', table_name, ['tenant_id'], unique=False)
    
    # Step 4: Update all existing records to use default tenant
    for table_name in tables_with_tenant:
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        if table_name in inspector.get_table_names():
            op.execute(f"""
                UPDATE {table_name}
                SET tenant_id = {default_tenant_id}
                WHERE tenant_id IS NULL
            """)
    
    # Step 5: Add foreign key constraints
    for table_name in tables_with_tenant:
        if table_name in inspector.get_table_names():
            # Check if foreign key already exists
            fk_name = f'fk_{table_name}_tenant_id'
            existing_fks = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
            if fk_name not in existing_fks:
                op.create_foreign_key(
                    fk_name,
                    table_name,
                    'tenants',
                    ['tenant_id'],
                    ['id']
                )
    
    # Step 6: Make tenant_id NOT NULL (only if it's currently nullable)
    for table_name in tables_with_tenant:
        if table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            tenant_col = next((col for col in columns if col['name'] == 'tenant_id'), None)
            if tenant_col and tenant_col['nullable']:
                op.alter_column(table_name, 'tenant_id', nullable=False)
    
    # Step 7: Drop old unique constraints and create composite unique indexes
    # Users: username should be unique per tenant
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Helper function to check if index exists
    def index_exists(name):
        result = connection.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :name"
        ), {"name": name})
        return result.fetchone() is not None
    
    if 'users' in inspector.get_table_names():
        # Drop old unique constraint on username if it exists
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'users_username_key'
                ) THEN
                    ALTER TABLE users DROP CONSTRAINT users_username_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_users_username_tenant'):
            op.create_index('idx_users_username_tenant', 'users', ['username', 'tenant_id'], unique=True)
    
    # Assets: asset_tag and serial_number should be unique per tenant
    if 'assets' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'assets_asset_tag_key'
                ) THEN
                    ALTER TABLE assets DROP CONSTRAINT assets_asset_tag_key;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'assets_serial_number_key'
                ) THEN
                    ALTER TABLE assets DROP CONSTRAINT assets_serial_number_key;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'assets_hostname_key'
                ) THEN
                    ALTER TABLE assets DROP CONSTRAINT assets_hostname_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_assets_tag_tenant'):
            op.create_index('idx_assets_tag_tenant', 'assets', ['asset_tag', 'tenant_id'], unique=True)
        if not index_exists('idx_assets_serial_tenant'):
            op.create_index('idx_assets_serial_tenant', 'assets', ['serial_number', 'tenant_id'], unique=True)
        if not index_exists('idx_assets_hostname_tenant'):
            op.create_index('idx_assets_hostname_tenant', 'assets', ['hostname', 'tenant_id'], unique=True, postgresql_where=sa.text('hostname IS NOT NULL'))
    
    # Asset Types: name should be unique per tenant
    if 'asset_types' in inspector.get_table_names():
        # Drop old unique constraint if it exists
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'asset_types_name_key'
                ) THEN
                    ALTER TABLE asset_types DROP CONSTRAINT asset_types_name_key;
                END IF;
            END $$;
        """)
        # Drop old unique index if it exists (SQLAlchemy creates ix_asset_types_name)
        op.execute("""
            DROP INDEX IF EXISTS ix_asset_types_name;
        """)
        # Create tenant-scoped composite unique index
        if not index_exists('idx_asset_types_name_tenant'):
            op.create_index('idx_asset_types_name_tenant', 'asset_types', ['name', 'tenant_id'], unique=True)
    
    # Datacenters: code should be unique per tenant
    if 'datacenters' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'datacenters_code_key'
                ) THEN
                    ALTER TABLE datacenters DROP CONSTRAINT datacenters_code_key;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'datacenters_name_key'
                ) THEN
                    ALTER TABLE datacenters DROP CONSTRAINT datacenters_name_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_datacenters_code_tenant'):
            op.create_index('idx_datacenters_code_tenant', 'datacenters', ['code', 'tenant_id'], unique=True)
        if not index_exists('idx_datacenters_name_tenant'):
            op.create_index('idx_datacenters_name_tenant', 'datacenters', ['name', 'tenant_id'], unique=True)
    
    # Racks: code should be unique per tenant
    if 'racks' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'racks_code_key'
                ) THEN
                    ALTER TABLE racks DROP CONSTRAINT racks_code_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_racks_code_tenant'):
            op.create_index('idx_racks_code_tenant', 'racks', ['code', 'tenant_id'], unique=True)
    
    # Storage Containers: name and barcode should be unique per tenant
    if 'storage_containers' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'storage_containers_name_key'
                ) THEN
                    ALTER TABLE storage_containers DROP CONSTRAINT storage_containers_name_key;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'storage_containers_barcode_key'
                ) THEN
                    ALTER TABLE storage_containers DROP CONSTRAINT storage_containers_barcode_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_storage_containers_name_tenant'):
            op.create_index('idx_storage_containers_name_tenant', 'storage_containers', ['name', 'tenant_id'], unique=True)
        if not index_exists('idx_storage_containers_barcode_tenant'):
            op.create_index('idx_storage_containers_barcode_tenant', 'storage_containers', ['barcode', 'tenant_id'], unique=True, postgresql_where=sa.text('barcode IS NOT NULL'))
    
    # Environmental Sensors: sensor_id should be unique per tenant
    if 'environmental_sensors' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'environmental_sensors_sensor_id_key'
                ) THEN
                    ALTER TABLE environmental_sensors DROP CONSTRAINT environmental_sensors_sensor_id_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_environmental_sensors_sensor_id_tenant'):
            op.create_index('idx_environmental_sensors_sensor_id_tenant', 'environmental_sensors', ['sensor_id', 'tenant_id'], unique=True)
    
    # Network Cables: serial_number should be unique per tenant
    if 'network_cables' in inspector.get_table_names():
        op.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'network_cables_serial_number_key'
                ) THEN
                    ALTER TABLE network_cables DROP CONSTRAINT network_cables_serial_number_key;
                END IF;
            END $$;
        """)
        if not index_exists('idx_network_cables_serial_tenant'):
            op.create_index('idx_network_cables_serial_tenant', 'network_cables', ['serial_number', 'tenant_id'], unique=True, postgresql_where=sa.text('serial_number IS NOT NULL'))


def downgrade() -> None:
    # Reverse the operations in reverse order
    
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Step 7: Restore old unique constraints (drop composite indexes)
    if 'network_cables' in inspector.get_table_names():
        op.drop_index('idx_network_cables_serial_tenant', table_name='network_cables')
        op.create_unique_constraint('network_cables_serial_number_key', 'network_cables', ['serial_number'])
    
    if 'environmental_sensors' in inspector.get_table_names():
        op.drop_index('idx_environmental_sensors_sensor_id_tenant', table_name='environmental_sensors')
        op.create_unique_constraint('environmental_sensors_sensor_id_key', 'environmental_sensors', ['sensor_id'])
    
    if 'storage_containers' in inspector.get_table_names():
        op.drop_index('idx_storage_containers_barcode_tenant', table_name='storage_containers')
        op.drop_index('idx_storage_containers_name_tenant', table_name='storage_containers')
        op.create_unique_constraint('storage_containers_barcode_key', 'storage_containers', ['barcode'])
        op.create_unique_constraint('storage_containers_name_key', 'storage_containers', ['name'])
    
    if 'racks' in inspector.get_table_names():
        op.drop_index('idx_racks_code_tenant', table_name='racks')
        op.create_unique_constraint('racks_code_key', 'racks', ['code'])
    
    if 'datacenters' in inspector.get_table_names():
        op.drop_index('idx_datacenters_name_tenant', table_name='datacenters')
        op.drop_index('idx_datacenters_code_tenant', table_name='datacenters')
        op.create_unique_constraint('datacenters_name_key', 'datacenters', ['name'])
        op.create_unique_constraint('datacenters_code_key', 'datacenters', ['code'])
    
    if 'asset_types' in inspector.get_table_names():
        op.drop_index('idx_asset_types_name_tenant', table_name='asset_types')
        op.create_unique_constraint('asset_types_name_key', 'asset_types', ['name'])
    
    if 'assets' in inspector.get_table_names():
        op.drop_index('idx_assets_hostname_tenant', table_name='assets')
        op.drop_index('idx_assets_serial_tenant', table_name='assets')
        op.drop_index('idx_assets_tag_tenant', table_name='assets')
        op.create_unique_constraint('assets_hostname_key', 'assets', ['hostname'])
        op.create_unique_constraint('assets_serial_number_key', 'assets', ['serial_number'])
        op.create_unique_constraint('assets_asset_tag_key', 'assets', ['asset_tag'])
    
    if 'users' in inspector.get_table_names():
        op.drop_index('idx_users_username_tenant', table_name='users')
        op.create_unique_constraint('users_username_key', 'users', ['username'])
    
    # Step 6: Make tenant_id nullable
    tables_with_tenant = [
        'users',
        'assets',
        'asset_lifecycle_events',
        'asset_types',
        'datacenters',
        'rooms',
        'racks',
        'rack_positions',
        'storage_containers',
        'maintenance_records',
        'maintenance_predictions',
        'workflows',
        'workflow_executions',
        'workflow_steps',
        'environmental_sensors',
        'environmental_readings',
        'network_ports',
        'network_connections',
        'vlans',
        'capacity_metrics',
        'power_metrics',
        'cooling_metrics',
        'network_cables',
        'power_cables',
    ]
    
    for table_name in tables_with_tenant:
        if table_name in inspector.get_table_names():
            op.alter_column(table_name, 'tenant_id', nullable=True)
    
    # Step 5: Drop foreign key constraints
    for table_name in tables_with_tenant:
        if table_name in inspector.get_table_names():
            op.drop_constraint(f'fk_{table_name}_tenant_id', table_name, type_='foreignkey')
    
    # Step 4: (No need to reverse data updates)
    
    # Step 3: Drop indexes and columns
    for table_name in tables_with_tenant:
        if table_name in inspector.get_table_names():
            op.drop_index(f'ix_{table_name}_tenant_id', table_name=table_name)
            op.drop_column(table_name, 'tenant_id')
    
    # Step 2: (No need to reverse default tenant creation)
    
    # Step 1: Drop tenants table
    op.drop_index('ix_tenants_slug', table_name='tenants')
    op.drop_index('ix_tenants_name', table_name='tenants')
    op.drop_index('ix_tenants_id', table_name='tenants')
    op.drop_table('tenants')

