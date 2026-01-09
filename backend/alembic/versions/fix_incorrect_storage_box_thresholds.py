"""fix_incorrect_storage_box_thresholds

Revision ID: fix_incorrect_storage_box_thresholds
Revises: 27153f7036ba
Create Date: 2025-11-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_incorrect_stock_thresholds'
down_revision: Union[str, None] = '27153f7036ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix assets that incorrectly have min_stock_threshold set but are NOT storage boxes.
    
    The previous migration (27153f7036ba) was too broad - it set min_stock_threshold = 1
    for ANY asset that had items in it. This incorrectly marked non-storage-box assets
    (like network devices, servers, storage_device equipment like SAN/NAS) as storage boxes.
    
    A storage BOX (for holding inventory items like cables) should ONLY be:
    1. asset_type = 'storage_box' (explicit storage box type)
    2. OR asset_tag matching 'DAC-%' or 'FIBER-%' (auto-generated cable boxes)
    
    Note: storage_device (equipment like SAN/NAS) is NOT a storage box and should NOT
    have min_stock_threshold set.
    
    This migration clears min_stock_threshold from any asset that doesn't meet these criteria.
    """
    # Clear min_stock_threshold from assets that are NOT storage boxes
    # A storage BOX is specifically for holding inventory items (cables, etc.)
    # A storage DEVICE (like SAN/NAS) is different - it's equipment, not a box
    # Only keep min_stock_threshold for:
    # 1. Explicit storage_box asset_type
    # 2. Assets with naming convention (DAC-*, FIBER-*) - these are auto-generated cable boxes
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = NULL
        WHERE min_stock_threshold IS NOT NULL
        AND NOT (
            -- Keep only explicit storage_box type (not storage_device which is equipment)
            asset_type = 'storage_box'
            -- Keep storage boxes by naming convention (auto-generated cable boxes)
            OR asset_tag LIKE 'DAC-%'
            OR asset_tag LIKE 'FIBER-%'
        )
    """)
    
    # Also fix any assets with min_stock_threshold = 0 (should be NULL)
    op.execute("""
        UPDATE assets
        SET min_stock_threshold = NULL
        WHERE min_stock_threshold = 0
    """)


def downgrade() -> None:
    """
    Cannot safely downgrade - we don't know which assets had min_stock_threshold
    set incorrectly vs correctly. This is a one-way data fix.
    """
    pass

