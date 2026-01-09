"""fix_min_stock_threshold_zero_to_null

Revision ID: 2f5ac940c23e
Revises: bb97c2a9c218
Create Date: 2025-11-22 01:17:50.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f5ac940c23e'
down_revision: Union[str, None] = 'bb97c2a9c218'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix storage boxes with min_stock_threshold = 0.
    A storage box with threshold 0 doesn't need to exist - set it to NULL.
    """
    # Set min_stock_threshold to NULL for any boxes with threshold = 0
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = NULL
        WHERE min_stock_threshold = 0
    """)


def downgrade() -> None:
    """
    Downgrade: Cannot restore the 0 values that were removed.
    This is a one-way data cleanup migration.
    """
    pass
