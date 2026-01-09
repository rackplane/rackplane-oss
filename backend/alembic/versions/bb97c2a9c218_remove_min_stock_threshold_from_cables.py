"""remove_min_stock_threshold_from_cables

Revision ID: bb97c2a9c218
Revises: 3e2854c5c0eb
Create Date: 2025-11-22 00:37:43.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb97c2a9c218'
down_revision: Union[str, None] = '3e2854c5c0eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove min_stock_threshold from all cable assets.
    Cables should never be storage boxes - they go INTO storage boxes.
    """
    # Update all cable assets to set min_stock_threshold to NULL
    # This includes: dac_cable, fiber_cable, ethernet_cable, network_cable, power_cable
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = NULL
        WHERE min_stock_threshold IS NOT NULL
        AND (
            asset_type ILIKE '%cable%'
            OR asset_type IN ('dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable')
        )
    """)


def downgrade() -> None:
    """
    Downgrade: Cannot restore min_stock_threshold values that were removed.
    This is a one-way data cleanup migration.
    """
    pass
