"""create catalog_skus table

Revision ID: 4a3b1c2d5e6f
Revises: d14b4938e66b
Create Date: 2024-12-04 18:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4a3b1c2d5e6f'
down_revision = 'd14b4938e66b'
branch_labels = None
depends_on = None


def upgrade():
    # Check if catalog_skus table already exists (may have been created by Base.metadata.create_all())
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'catalog_skus' in existing_tables:
        # Table already exists - skip creation
        return
    
    # Create catalog_skus table
    op.create_table(
        'catalog_skus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor', sa.String(length=100), nullable=False, comment='Vendor name (e.g., FS.com, NVIDIA)'),
        sa.Column('sku', sa.String(length=200), nullable=False, comment="Product SKU (vendor's internal SKU number)"),
        sa.Column('part_number', sa.String(length=200), nullable=True, comment='Product part number (customer-facing identifier)'),
        sa.Column('name', sa.String(length=500), nullable=False, comment='Product name/description'),
        sa.Column('manufacturer', sa.String(length=100), nullable=True, comment='Manufacturer'),
        sa.Column('asset_type', sa.String(length=100), nullable=True, comment='Asset type (dac_cable, optical_transceiver, etc.)'),
        sa.Column('specifications', sa.JSON(), nullable=True, comment='Product specifications (speed, length, connectors, etc.)'),
        sa.Column('price_usd', sa.Float(), nullable=True, comment='Price in USD'),
        sa.Column('currency', sa.String(length=10), nullable=True, comment='Currency code'),
        sa.Column('price_updated_at', sa.DateTime(), nullable=True, comment='When price was last updated'),
        sa.Column('compatibility', sa.JSON(), nullable=True, comment='Compatible devices/models'),
        sa.Column('description', sa.Text(), nullable=True, comment='Detailed product description'),
        sa.Column('datasheet_url', sa.String(length=500), nullable=True, comment='Link to product datasheet'),
        sa.Column('vendor_url', sa.String(length=500), nullable=True, comment='Link to vendor product page'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Whether this SKU is visible'),
        sa.Column('source_id', sa.String(length=100), nullable=True, comment='ID in the upstream RackPlane API (if synced)'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True, comment='When this record was last synced from upstream'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_catalog_skus_id'), 'catalog_skus', ['id'], unique=False)
    op.create_index(op.f('ix_catalog_skus_vendor'), 'catalog_skus', ['vendor'], unique=False)
    op.create_index(op.f('ix_catalog_skus_sku'), 'catalog_skus', ['sku'], unique=False)
    op.create_index('ix_catalog_sku_vendor_sku', 'catalog_skus', ['vendor', 'sku'], unique=True)
    op.create_index(op.f('ix_catalog_skus_part_number'), 'catalog_skus', ['part_number'], unique=False)
    op.create_index(op.f('ix_catalog_skus_asset_type'), 'catalog_skus', ['asset_type'], unique=False)
    op.create_index(op.f('ix_catalog_skus_is_active'), 'catalog_skus', ['is_active'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_catalog_skus_is_active'), table_name='catalog_skus')
    op.drop_index(op.f('ix_catalog_skus_asset_type'), table_name='catalog_skus')
    op.drop_index(op.f('ix_catalog_skus_part_number'), table_name='catalog_skus')
    op.drop_index('ix_catalog_sku_vendor_sku', table_name='catalog_skus')
    op.drop_index(op.f('ix_catalog_skus_sku'), table_name='catalog_skus')
    op.drop_index(op.f('ix_catalog_skus_vendor'), table_name='catalog_skus')
    op.drop_index(op.f('ix_catalog_skus_id'), table_name='catalog_skus')
    op.drop_table('catalog_skus')
