"""set null storage box thresholds to one

Revision ID: 27153f7036ba
Revises: f1bb2a847c92
Create Date: 2025-11-22 02:14:29.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27153f7036ba'
down_revision: Union[str, None] = 'f1bb2a847c92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Set all storage boxes with NULL min_stock_threshold to 1.
    
    A storage box is identified by:
    1. Having asset_type containing 'storage' or being 'storage_device' or 'storage_box'
    2. OR having asset_tag matching storage box naming conventions (DAC-* or FIBER-*)
    3. OR having min_stock_threshold > 0 (but we're fixing NULL ones, so this doesn't apply)
    
    Any storage box must have min_stock_threshold >= 1. If you don't want to track it, delete it.
    """
    connection = op.get_bind()
    
    # Update storage boxes by asset_type
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = 1
        WHERE min_stock_threshold IS NULL
        AND (
            asset_type ILIKE '%storage%'
            OR asset_type IN ('storage_device', 'storage_box')
        )
    """)
    
    # Update storage boxes by naming convention (DAC-* or FIBER-*)
    # These are auto-generated storage boxes for cables
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = 1
        WHERE min_stock_threshold IS NULL
        AND (
            asset_tag LIKE 'DAC-%'
            OR asset_tag LIKE 'FIBER-%'
        )
    """)
    
    # Also update any assets that have items in them (container_id points to them)
    # If an asset has items, it's likely a storage box
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = 1
        WHERE min_stock_threshold IS NULL
        AND id IN (
            SELECT DISTINCT container_id
            FROM assets
            WHERE container_id IS NOT NULL
        )
    """)


def downgrade() -> None:
    """
    Cannot safely downgrade - we don't know which boxes were NULL vs set to 1.
    This is a one-way data fix.
    """
    pass
