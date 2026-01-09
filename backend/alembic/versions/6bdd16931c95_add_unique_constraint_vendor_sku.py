"""add_unique_constraint_vendor_sku

Revision ID: 6bdd16931c95
Revises: 2ee961fe5968
Create Date: 2025-12-04 20:58:34.188472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bdd16931c95'
down_revision: Union[str, None] = '2ee961fe5968'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, remove any existing duplicates (keep the one with the lowest ID)
    # This is done via a subquery that deletes duplicates
    op.execute("""
        DELETE FROM vendor_skus
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY tenant_id, LOWER(vendor), LOWER(sku) ORDER BY id) as rn
                FROM vendor_skus
            ) t
            WHERE t.rn > 1
        )
    """)
    
    # Check if index already exists before creating (idempotency)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'ix_vendor_skus_tenant_vendor_sku_unique'
    """))
    index_exists = result.fetchone() is not None
    
    if not index_exists:
        # Add unique constraint on (tenant_id, vendor, sku)
        # Using LOWER() to make it case-insensitive
        op.create_index(
            'ix_vendor_skus_tenant_vendor_sku_unique',
            'vendor_skus',
            [sa.text('tenant_id'), sa.text('LOWER(vendor)'), sa.text('LOWER(sku)')],
            unique=True
        )


def downgrade() -> None:
    # Check if index exists before dropping (idempotency)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'ix_vendor_skus_tenant_vendor_sku_unique'
    """))
    index_exists = result.fetchone() is not None
    
    if index_exists:
        # Remove the unique constraint
        op.drop_index('ix_vendor_skus_tenant_vendor_sku_unique', table_name='vendor_skus')

