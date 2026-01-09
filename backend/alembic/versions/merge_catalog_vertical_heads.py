"""merge catalog vertical heads (single head after chain fix)

Revision ID: merge_catalog_vertical_heads
Revises: add_catalog_vertical
Create Date: 2025-12-26 04:00:00.000000

This migration exists to maintain a clean merge point after fixing the
add_catalog_vertical migration to properly chain from merge_whitelabel_cart.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_catalog_vertical_heads'
down_revision: Union[str, Sequence[str], None] = 'add_catalog_vertical'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

