"""add image_url to sku models

Revision ID: 535df0b78c56
Revises: ba21f362d341
Create Date: 2025-12-23 23:00:08.563429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '535df0b78c56'
down_revision: Union[str, None] = 'ba21f362d341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add image_url to vendor_skus if missing
    columns = [c['name'] for c in inspector.get_columns('vendor_skus')]
    if 'image_url' not in columns:
        with op.batch_alter_table('vendor_skus', schema=None) as batch_op:
            batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True, comment='Link to product image'))

    # Add image_url to catalog_skus if missing
    columns = [c['name'] for c in inspector.get_columns('catalog_skus')]
    if 'image_url' not in columns:
        with op.batch_alter_table('catalog_skus', schema=None) as batch_op:
            batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True, comment='Link to product image'))

    # Add image_url to global_product_catalog if missing
    columns = [c['name'] for c in inspector.get_columns('global_product_catalog')]
    if 'image_url' not in columns:
        with op.batch_alter_table('global_product_catalog', schema=None) as batch_op:
            batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True, comment='Link to product image'))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    for table_name in ['global_product_catalog', 'catalog_skus', 'vendor_skus']:
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        if 'image_url' in columns:
            with op.batch_alter_table(table_name, schema=None) as batch_op:
                batch_op.drop_column('image_url')

