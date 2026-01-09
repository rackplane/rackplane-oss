"""restore_missing_constraints

Revision ID: c6ea09d24faf
Revises: add_token_id_to_audit_logs
Create Date: 2025-12-01 21:13:02.179865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6ea09d24faf'
down_revision: Union[str, None] = 'add_token_id_to_audit_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Restore critical unique constraints that prevent duplicate data.
    
    These constraints were missing from the database, which could lead to
    duplicate asset tags, serial numbers, hostnames, datacenter codes, etc.
    This migration restores all critical constraints to ensure data integrity.
    
    CRITICAL: These constraints MUST exist to prevent duplicate data issues
    that have occurred in the past (e.g., 77,820 duplicate users).
    
    Note: The cff3b4de952b migration dropped storage_containers constraints
    without recreating them. This migration restores them.
    """
    import sqlalchemy as sa
    from sqlalchemy import inspect
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Helper function to safely create index if it doesn't exist
    def create_unique_index_if_not_exists(index_name: str, table_name: str, columns: list, where_clause: str = None):
        """Create a unique index only if it doesn't already exist."""
        # Check if index already exists using SQL (more reliable)
        check_sql = sa.text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = :table_name AND indexname = :index_name
        """)
        result = connection.execute(check_sql, {
            'table_name': table_name,
            'index_name': index_name
        })
        exists = result.scalar() > 0
        
        if exists:
            # Index exists, check if it's unique
            check_unique_sql = sa.text("""
                SELECT indexdef 
                FROM pg_indexes 
                WHERE tablename = :table_name AND indexname = :index_name
            """)
            result = connection.execute(check_unique_sql, {
                'table_name': table_name,
                'index_name': index_name
            })
            indexdef = result.scalar()
            if indexdef and 'UNIQUE' in indexdef.upper():
                # Index exists and is unique - skip
                return
            else:
                # Index exists but isn't unique - drop and recreate
                op.drop_index(index_name, table_name=table_name)
        
        # Create the index using raw SQL for more control
        columns_str = ', '.join(columns)
        if where_clause:
            create_sql = f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {index_name} 
                ON {table_name} ({columns_str}) 
                WHERE {where_clause}
            """
        else:
            create_sql = f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {index_name} 
                ON {table_name} ({columns_str})
            """
        connection.execute(sa.text(create_sql))
        connection.commit()
    
    # 1. Assets: asset_tag, serial_number, hostname should be unique per tenant
    if 'assets' in inspector.get_table_names():
        create_unique_index_if_not_exists(
            'idx_assets_tag_tenant',
            'assets',
            ['asset_tag', 'tenant_id']
        )
        create_unique_index_if_not_exists(
            'idx_assets_serial_tenant',
            'assets',
            ['serial_number', 'tenant_id']
        )
        create_unique_index_if_not_exists(
            'idx_assets_hostname_tenant',
            'assets',
            ['hostname', 'tenant_id'],
            where_clause='hostname IS NOT NULL'
        )
    
    # 2. Asset Types: name should be unique per tenant
    if 'asset_types' in inspector.get_table_names():
        create_unique_index_if_not_exists(
            'idx_asset_types_name_tenant',
            'asset_types',
            ['name', 'tenant_id']
        )
    
    # 3. Datacenters: name and code should be unique per tenant
    if 'datacenters' in inspector.get_table_names():
        create_unique_index_if_not_exists(
            'idx_datacenters_name_tenant',
            'datacenters',
            ['name', 'tenant_id']
        )
        create_unique_index_if_not_exists(
            'idx_datacenters_code_tenant',
            'datacenters',
            ['code', 'tenant_id']
        )
    
    # 4. Environmental Sensors: sensor_id should be unique per tenant
    if 'environmental_sensors' in inspector.get_table_names():
        create_unique_index_if_not_exists(
            'idx_environmental_sensors_sensor_id_tenant',
            'environmental_sensors',
            ['sensor_id', 'tenant_id']
        )
    
    # 5. Storage Containers: name and barcode should be unique per tenant
    if 'storage_containers' in inspector.get_table_names():
        create_unique_index_if_not_exists(
            'idx_storage_containers_name_tenant',
            'storage_containers',
            ['name', 'tenant_id']
        )
        create_unique_index_if_not_exists(
            'idx_storage_containers_barcode_tenant',
            'storage_containers',
            ['barcode', 'tenant_id'],
            where_clause='barcode IS NOT NULL'
        )


def downgrade() -> None:
    """
    WARNING: This downgrade intentionally does NOT drop the constraints.
    
    These constraints are CRITICAL for data integrity and should NEVER be dropped.
    Dropping them would allow duplicate data, which has caused serious issues in the past.
    
    If you absolutely must remove these constraints, do so manually and with extreme caution.
    """
    # Intentionally empty - we do NOT want to drop these critical constraints
    pass

