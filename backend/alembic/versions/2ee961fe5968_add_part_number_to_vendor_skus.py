"""add_part_number_to_vendor_skus

Revision ID: 2ee961fe5968
Revises: 3e5be52425ee
Create Date: 2025-12-04 20:54:30.623581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ee961fe5968'
down_revision: Union[str, None] = '3e5be52425ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add part_number column to vendor_skus table (with existence check)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'vendor_skus' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('vendor_skus')]
        
        if 'part_number' not in columns:
            op.add_column('vendor_skus', sa.Column('part_number', sa.String(length=200), nullable=True))
        
        indexes = [idx['name'] for idx in inspector.get_indexes('vendor_skus')]
        if 'ix_vendor_skus_part_number' not in indexes:
            op.create_index(op.f('ix_vendor_skus_part_number'), 'vendor_skus', ['part_number'], unique=False)


def downgrade() -> None:
    # Remove part_number column and index (with existence check)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'vendor_skus' in inspector.get_table_names():
        indexes = [idx['name'] for idx in inspector.get_indexes('vendor_skus')]
        if 'ix_vendor_skus_part_number' in indexes:
            op.drop_index(op.f('ix_vendor_skus_part_number'), table_name='vendor_skus')
        
        columns = [col['name'] for col in inspector.get_columns('vendor_skus')]
        if 'part_number' in columns:
            op.drop_column('vendor_skus', 'part_number')

