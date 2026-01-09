"""add_vendor_skus_table

Revision ID: add_vendor_skus
Revises: 30805a5e63dc
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_vendor_skus'
down_revision: Union[str, Sequence[str], None] = '30805a5e63dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create vendor_skus table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'vendor_skus' not in existing_tables:
        op.create_table(
            'vendor_skus',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vendor', sa.String(length=100), nullable=False),
            sa.Column('sku', sa.String(length=200), nullable=False),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('asset_type', sa.String(length=100), nullable=True),
            sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('price_usd', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=True, server_default='USD'),
            sa.Column('price_updated_at', sa.DateTime(), nullable=True),
            sa.Column('compatibility', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('datasheet_url', sa.String(length=500), nullable=True),
            sa.Column('vendor_url', sa.String(length=500), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('last_verified', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vendor_skus_id'), 'vendor_skus', ['id'], unique=False)
        op.create_index(op.f('ix_vendor_skus_vendor'), 'vendor_skus', ['vendor'], unique=False)
        op.create_index(op.f('ix_vendor_skus_sku'), 'vendor_skus', ['sku'], unique=False)
        op.create_index(op.f('ix_vendor_skus_manufacturer'), 'vendor_skus', ['manufacturer'], unique=False)
        op.create_index(op.f('ix_vendor_skus_asset_type'), 'vendor_skus', ['asset_type'], unique=False)
        op.create_index(op.f('ix_vendor_skus_is_active'), 'vendor_skus', ['is_active'], unique=False)
        op.create_index(op.f('ix_vendor_skus_tenant_id'), 'vendor_skus', ['tenant_id'], unique=False)
        op.create_index('ix_vendor_sku_vendor_sku', 'vendor_skus', ['vendor', 'sku'], unique=False)
    else:
        # Table already exists, just ensure indexes exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('vendor_skus')]
        indexes_to_create = [
            ('ix_vendor_skus_id', ['id']),
            ('ix_vendor_skus_vendor', ['vendor']),
            ('ix_vendor_skus_sku', ['sku']),
            ('ix_vendor_skus_manufacturer', ['manufacturer']),
            ('ix_vendor_skus_asset_type', ['asset_type']),
            ('ix_vendor_skus_is_active', ['is_active']),
            ('ix_vendor_skus_tenant_id', ['tenant_id']),
            ('ix_vendor_sku_vendor_sku', ['vendor', 'sku']),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                if len(columns) == 1:
                    op.create_index(op.f(idx_name), 'vendor_skus', columns, unique=False)
                else:
                    op.create_index(idx_name, 'vendor_skus', columns, unique=False)


def downgrade() -> None:
    op.drop_index('ix_vendor_sku_vendor_sku', table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_tenant_id'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_is_active'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_asset_type'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_manufacturer'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_sku'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_vendor'), table_name='vendor_skus')
    op.drop_index(op.f('ix_vendor_skus_id'), table_name='vendor_skus')
    op.drop_table('vendor_skus')

