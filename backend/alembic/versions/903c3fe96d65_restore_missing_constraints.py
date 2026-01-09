"""restore_missing_constraints

Revision ID: 903c3fe96d65
Revises: 9110dc4f049d
Create Date: 2025-12-24 04:48:31.870837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '903c3fe96d65'
down_revision: Union[str, None] = '9110dc4f049d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def index_exists(conn, index_name: str) -> bool:
    """Check if an index exists in pg_indexes."""
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint exists in pg_constraint OR pg_indexes.
    
    PostgreSQL unique constraints also create backing indexes with the same name,
    so we need to check both to avoid 'relation already exists' errors.
    """
    # Check pg_constraint first
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name"
    ), {"name": constraint_name})
    if result.fetchone() is not None:
        return True
    
    # Also check pg_indexes (unique constraints create backing indexes)
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": constraint_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()
    
    # idx_api_keys_user_label_tenant (partial unique index)
    if not index_exists(conn, 'idx_api_keys_user_label_tenant'):
        op.create_index('idx_api_keys_user_label_tenant', 'api_keys', ['user_id', 'label', 'tenant_id'], unique=True, postgresql_where=sa.text('label IS NOT NULL'))
    
    # idx_asset_types_name_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_asset_types_name_tenant'):
        op.create_unique_constraint('idx_asset_types_name_tenant', 'asset_types', ['name', 'tenant_id'])
    
    # idx_assets_hostname_tenant (partial unique index)
    if not index_exists(conn, 'idx_assets_hostname_tenant'):
        op.create_index('idx_assets_hostname_tenant', 'assets', ['hostname', 'tenant_id'], unique=True, postgresql_where=sa.text('hostname IS NOT NULL'))
    
    # idx_assets_serial_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_assets_serial_tenant'):
        op.create_unique_constraint('idx_assets_serial_tenant', 'assets', ['serial_number', 'tenant_id'])
    
    # idx_assets_tag_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_assets_tag_tenant'):
        op.create_unique_constraint('idx_assets_tag_tenant', 'assets', ['asset_tag', 'tenant_id'])
    
    # idx_audit_logs_unique_action (unique constraint)
    if not constraint_exists(conn, 'idx_audit_logs_unique_action'):
        op.create_unique_constraint('idx_audit_logs_unique_action', 'audit_logs', ['action', 'user_id', 'username', 'table_name', 'record_id', 'created_at'])
    
    # idx_datacenters_code_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_datacenters_code_tenant'):
        op.create_unique_constraint('idx_datacenters_code_tenant', 'datacenters', ['code', 'tenant_id'])
    
    # idx_datacenters_name_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_datacenters_name_tenant'):
        op.create_unique_constraint('idx_datacenters_name_tenant', 'datacenters', ['name', 'tenant_id'])
    
    # idx_environmental_sensors_sensor_id_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_environmental_sensors_sensor_id_tenant'):
        op.create_unique_constraint('idx_environmental_sensors_sensor_id_tenant', 'environmental_sensors', ['sensor_id', 'tenant_id'])
    
    # idx_network_cables_serial_tenant (partial unique index)
    if not index_exists(conn, 'idx_network_cables_serial_tenant'):
        op.create_index('idx_network_cables_serial_tenant', 'network_cables', ['serial_number', 'tenant_id'], unique=True, postgresql_where=sa.text('serial_number IS NOT NULL'))
    
    # idx_racks_code_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_racks_code_tenant'):
        op.create_unique_constraint('idx_racks_code_tenant', 'racks', ['code', 'tenant_id'])
    
    # idx_storage_containers_barcode_tenant (partial unique index)
    if not index_exists(conn, 'idx_storage_containers_barcode_tenant'):
        op.create_index('idx_storage_containers_barcode_tenant', 'storage_containers', ['barcode', 'tenant_id'], unique=True, postgresql_where=sa.text('barcode IS NOT NULL'))
    
    # idx_storage_containers_name_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_storage_containers_name_tenant'):
        op.create_unique_constraint('idx_storage_containers_name_tenant', 'storage_containers', ['name', 'tenant_id'])
    
    # idx_users_username_tenant (unique constraint)
    if not constraint_exists(conn, 'idx_users_username_tenant'):
        op.create_unique_constraint('idx_users_username_tenant', 'users', ['username', 'tenant_id'])
    
    # Drop old vendor_sku index if exists, create new one
    if index_exists(conn, 'ix_vendor_sku_vendor_sku'):
        op.drop_index('ix_vendor_sku_vendor_sku', table_name='vendor_skus')
    
    if not index_exists(conn, 'ix_vendor_skus_tenant_vendor_sku_unique'):
        op.create_index('ix_vendor_skus_tenant_vendor_sku_unique', 'vendor_skus', ['tenant_id', sa.text('lower(vendor)'), sa.text('lower(sku)')], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    
    # Drop new vendor_sku index, recreate old one
    if index_exists(conn, 'ix_vendor_skus_tenant_vendor_sku_unique'):
        op.drop_index('ix_vendor_skus_tenant_vendor_sku_unique', table_name='vendor_skus')
    
    if not index_exists(conn, 'ix_vendor_sku_vendor_sku'):
        op.create_index('ix_vendor_sku_vendor_sku', 'vendor_skus', ['vendor', 'sku'], unique=False)
    
    # Drop all constraints/indexes if they exist
    if constraint_exists(conn, 'idx_users_username_tenant'):
        op.drop_constraint('idx_users_username_tenant', 'users', type_='unique')
    
    if constraint_exists(conn, 'idx_storage_containers_name_tenant'):
        op.drop_constraint('idx_storage_containers_name_tenant', 'storage_containers', type_='unique')
    
    if index_exists(conn, 'idx_storage_containers_barcode_tenant'):
        op.drop_index('idx_storage_containers_barcode_tenant', table_name='storage_containers', postgresql_where=sa.text('barcode IS NOT NULL'))
    
    if constraint_exists(conn, 'idx_racks_code_tenant'):
        op.drop_constraint('idx_racks_code_tenant', 'racks', type_='unique')
    
    if index_exists(conn, 'idx_network_cables_serial_tenant'):
        op.drop_index('idx_network_cables_serial_tenant', table_name='network_cables', postgresql_where=sa.text('serial_number IS NOT NULL'))
    
    if constraint_exists(conn, 'idx_environmental_sensors_sensor_id_tenant'):
        op.drop_constraint('idx_environmental_sensors_sensor_id_tenant', 'environmental_sensors', type_='unique')
    
    if constraint_exists(conn, 'idx_datacenters_name_tenant'):
        op.drop_constraint('idx_datacenters_name_tenant', 'datacenters', type_='unique')
    
    if constraint_exists(conn, 'idx_datacenters_code_tenant'):
        op.drop_constraint('idx_datacenters_code_tenant', 'datacenters', type_='unique')
    
    if constraint_exists(conn, 'idx_audit_logs_unique_action'):
        op.drop_constraint('idx_audit_logs_unique_action', 'audit_logs', type_='unique')
    
    if constraint_exists(conn, 'idx_assets_tag_tenant'):
        op.drop_constraint('idx_assets_tag_tenant', 'assets', type_='unique')
    
    if constraint_exists(conn, 'idx_assets_serial_tenant'):
        op.drop_constraint('idx_assets_serial_tenant', 'assets', type_='unique')
    
    if index_exists(conn, 'idx_assets_hostname_tenant'):
        op.drop_index('idx_assets_hostname_tenant', table_name='assets', postgresql_where=sa.text('hostname IS NOT NULL'))
    
    if constraint_exists(conn, 'idx_asset_types_name_tenant'):
        op.drop_constraint('idx_asset_types_name_tenant', 'asset_types', type_='unique')
    
    if index_exists(conn, 'idx_api_keys_user_label_tenant'):
        op.drop_index('idx_api_keys_user_label_tenant', table_name='api_keys', postgresql_where=sa.text('label IS NOT NULL'))
