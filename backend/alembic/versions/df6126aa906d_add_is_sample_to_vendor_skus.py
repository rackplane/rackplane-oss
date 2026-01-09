"""add_is_sample_to_vendor_skus

Revision ID: df6126aa906d
Revises: 6bdd16931c95
Create Date: 2025-12-04 22:03:18.356393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df6126aa906d'
down_revision: Union[str, None] = '6bdd16931c95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if vendor_skus table exists
    if 'vendor_skus' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('vendor_skus')]
        
        # Add is_sample column if it doesn't exist
        if 'is_sample' not in columns:
            op.add_column('vendor_skus', sa.Column('is_sample', sa.Boolean(), nullable=False, server_default='false', comment='Whether this is a sample/preview SKU from RackPlane (tenant_id=0)'))
        
        # Check if index exists, create if not
        indexes = [idx['name'] for idx in inspector.get_indexes('vendor_skus')]
        if 'ix_vendor_skus_is_sample' not in indexes:
            op.create_index('ix_vendor_skus_is_sample', 'vendor_skus', ['is_sample'], unique=False)


def downgrade() -> None:
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'vendor_skus' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('vendor_skus')]
        
        # Drop index if it exists
        indexes = [idx['name'] for idx in inspector.get_indexes('vendor_skus')]
        if 'ix_vendor_skus_is_sample' in indexes:
            op.drop_index('ix_vendor_skus_is_sample', table_name='vendor_skus')
        
        # Drop column if it exists
        if 'is_sample' in columns:
            op.drop_column('vendor_skus', 'is_sample')

