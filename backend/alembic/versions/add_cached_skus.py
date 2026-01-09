"""Add cached_skus table for offline mode

Revision ID: add_cached_skus
Revises: 0c530a5e0d19
Create Date: 2024-12-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cached_skus'
down_revision = '0c530a5e0d19'
branch_labels = None
depends_on = None



def upgrade() -> None:
    # Check if table already exists to make migration idempotent
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'cached_skus' not in tables:
        op.create_table(
            'cached_skus',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
            sa.Column('sku', sa.String(100), index=True),
            sa.Column('part_number', sa.String(100), index=True),
            sa.Column('vendor', sa.String(50)),
            sa.Column('name', sa.String(255)),
            sa.Column('manufacturer', sa.String(100)),
            sa.Column('asset_type', sa.String(50)),
            sa.Column('specifications', sa.JSON()),
            sa.Column('description', sa.Text()),
            sa.Column('image_url', sa.String(500)),
            sa.Column('datasheet_url', sa.String(500)),
            sa.Column('vendor_url', sa.String(500)),
            sa.Column('price_usd', sa.String(20)),
            sa.Column('currency', sa.String(10), server_default='USD'),
            sa.Column('fetched_at', sa.DateTime()),
            sa.Column('expires_at', sa.DateTime()),
            sa.Column('source', sa.String(50)),
        )
        
        # Create composite indexes for common lookups
        op.create_index('ix_cached_skus_tenant_sku', 'cached_skus', ['tenant_id', 'sku'])
        op.create_index('ix_cached_skus_tenant_part', 'cached_skus', ['tenant_id', 'part_number'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'cached_skus' in tables:
        # Check indexes before dropping to be safe
        indexes = [i['name'] for i in inspector.get_indexes('cached_skus')]
        
        if 'ix_cached_skus_tenant_part' in indexes:
            op.drop_index('ix_cached_skus_tenant_part', 'cached_skus')
        if 'ix_cached_skus_tenant_sku' in indexes:
            op.drop_index('ix_cached_skus_tenant_sku', 'cached_skus')
            
        op.drop_table('cached_skus')

