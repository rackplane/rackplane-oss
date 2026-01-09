"""add global product catalog and fs integration models

Revision ID: add_global_cat
Revises: fix_missing_cols
Create Date: 2025-12-11 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_global_cat'
down_revision = 'fix_missing_cols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. fs_api_usage
    if 'fs_api_usage' not in tables:
        op.create_table('fs_api_usage',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.String(length=200), nullable=False),
            sa.Column('method', sa.String(length=20), nullable=True),
            sa.Column('status_code', sa.Integer(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=True),
            sa.Column('request_id', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_fs_api_usage_created_at'), 'fs_api_usage', ['created_at'], unique=False)
        op.create_index(op.f('ix_fs_api_usage_endpoint'), 'fs_api_usage', ['endpoint'], unique=False)
        op.create_index(op.f('ix_fs_api_usage_id'), 'fs_api_usage', ['id'], unique=False)

    # 2. global_product_catalog
    if 'global_product_catalog' not in tables:
        op.create_table('global_product_catalog',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vendor', sa.String(length=50), nullable=False),
            sa.Column('vendor_product_id', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('part_number', sa.String(length=200), nullable=True),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.Column('form_factor', sa.String(length=50), nullable=True),
            sa.Column('speed', sa.String(length=50), nullable=True),
            sa.Column('interface', sa.String(length=100), nullable=True),
            sa.Column('specs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('price_usd', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=True),
            sa.Column('datasheet_url', sa.String(length=500), nullable=True),
            sa.Column('product_url', sa.String(length=500), nullable=True),
            sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_global_catalog_search', 'global_product_catalog', ['name', 'part_number', 'manufacturer'], unique=False)
        op.create_index('ix_global_catalog_vendor_id', 'global_product_catalog', ['vendor', 'vendor_product_id'], unique=True)
        op.create_index(op.f('ix_global_product_catalog_category'), 'global_product_catalog', ['category'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_form_factor'), 'global_product_catalog', ['form_factor'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_id'), 'global_product_catalog', ['id'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_manufacturer'), 'global_product_catalog', ['manufacturer'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_part_number'), 'global_product_catalog', ['part_number'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_vend_prod_id'), 'global_product_catalog', ['vendor_product_id'], unique=False)
        op.create_index(op.f('ix_global_product_catalog_vendor'), 'global_product_catalog', ['vendor'], unique=False)

    # 3. fs_order_cache
    if 'fs_order_cache' not in tables:
        op.create_table('fs_order_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.String(length=50), nullable=False),
            sa.Column('order_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column('total_amount', sa.String(length=50), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=True),
            sa.Column('order_date', sa.String(length=20), nullable=True),
            sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_fs_order_cache_id'), 'fs_order_cache', ['id'], unique=False)
        op.create_index(op.f('ix_fs_order_cache_order_id'), 'fs_order_cache', ['order_id'], unique=True)

    # 4. fs_warranty_cache
    if 'fs_warranty_cache' not in tables:
        op.create_table('fs_warranty_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.String(length=50), nullable=False),
            sa.Column('serial_number', sa.String(length=100), nullable=True),
            sa.Column('product_id', sa.String(length=50), nullable=True),
            sa.Column('product_name', sa.String(length=500), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=True),
            sa.Column('warranty_start', sa.Date(), nullable=True),
            sa.Column('warranty_end', sa.Date(), nullable=True),
            sa.Column('warranty_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_fs_warranty_cache_id'), 'fs_warranty_cache', ['id'], unique=False)
        op.create_index('ix_fs_warranty_order_serial', 'fs_warranty_cache', ['order_id', 'serial_number'], unique=False)
        op.create_index(op.f('ix_fs_warranty_cache_order_id'), 'fs_warranty_cache', ['order_id'], unique=False)
        op.create_index(op.f('ix_fs_warranty_cache_serial_number'), 'fs_warranty_cache', ['serial_number'], unique=False)

    # 5. vendor_skus modification
    if 'vendor_skus' in tables:
        columns = [c['name'] for c in inspector.get_columns('vendor_skus')]
        if 'global_catalog_id' not in columns:
            op.add_column('vendor_skus', sa.Column('global_catalog_id', sa.Integer(), nullable=True, comment='Pointer to global_product_catalog. If set, SKU details are fetched from there.'))
            op.create_index(op.f('ix_vendor_skus_global_catalog_id'), 'vendor_skus', ['global_catalog_id'], unique=False)
            op.create_foreign_key(None, 'vendor_skus', 'global_product_catalog', ['global_catalog_id'], ['id'])


def downgrade() -> None:
    # Basic downgrade logic
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'vendor_skus' in tables:
        columns = [c['name'] for c in inspector.get_columns('vendor_skus')]
        if 'global_catalog_id' in columns:
            op.drop_column('vendor_skus', 'global_catalog_id')

    if 'fs_warranty_cache' in tables:
        op.drop_table('fs_warranty_cache')

    if 'fs_order_cache' in tables:
        op.drop_table('fs_order_cache')

    if 'global_product_catalog' in tables:
        op.drop_table('global_product_catalog')

    if 'fs_api_usage' in tables:
        op.drop_table('fs_api_usage')
