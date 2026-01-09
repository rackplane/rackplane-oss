"""add max_quantity to container stock thresholds

Revision ID: 9110dc4f049d
Revises: add_plugin_config
Create Date: 2025-12-24 04:42:02.396644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9110dc4f049d'
down_revision: Union[str, None] = 'add_plugin_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column exists to Ensure Idempotency
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('container_stock_thresholds')]
    
    if 'max_quantity' not in columns:
        op.add_column('container_stock_thresholds', sa.Column('max_quantity', sa.Integer(), nullable=True, comment='Maximum stock level (Par Level) for this item type'))


def downgrade() -> None:
    # Revert changes
    op.drop_column('container_stock_thresholds', 'max_quantity')
