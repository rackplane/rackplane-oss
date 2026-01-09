"""add_inventory_lifecycle_fields

Revision ID: 1b05f9f43610
Revises: 1524faedfd1f
Create Date: 2025-11-21 16:21:47.824280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b05f9f43610'
down_revision: Union[str, None] = '1524faedfd1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check what exists before trying to create
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if assets table exists first
    existing_tables = inspector.get_table_names()
    if 'assets' not in existing_tables:
        # Assets table doesn't exist yet - this migration will be applied later
        # when the assets table is created by an earlier migration
        return
    
    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    # Add container_id column if it doesn't exist
    if 'container_id' not in columns:
        op.add_column('assets', sa.Column('container_id', sa.Integer(), nullable=True))
    
    # Get existing foreign keys
    fks = inspector.get_foreign_keys('assets')
    fk_names = [fk['name'] for fk in fks]
    
    # Create foreign key if it doesn't exist
    if 'fk_assets_container_id' not in fk_names:
        op.create_foreign_key(
            'fk_assets_container_id',
            'assets', 'assets',
            ['container_id'], ['id']
        )
    
    # Get existing indexes
    indexes = inspector.get_indexes('assets')
    index_names = [idx['name'] for idx in indexes]
    
    # Create index if it doesn't exist
    if 'ix_assets_container_id' not in index_names:
        op.create_index('ix_assets_container_id', 'assets', ['container_id'], unique=False)
    
    # Add min_stock_threshold column if it doesn't exist
    if 'min_stock_threshold' not in columns:
        op.add_column('assets', sa.Column('min_stock_threshold', sa.Integer(), nullable=True, server_default='0'))
    
    # Note: IN_STORAGE and RMA enum values are handled at application level
    # PostgreSQL enum updates require special handling (ALTER TYPE)


def downgrade() -> None:
    op.drop_index('ix_assets_container_id', table_name='assets')
    op.drop_constraint('fk_assets_container_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'container_id')
    op.drop_column('assets', 'min_stock_threshold')

