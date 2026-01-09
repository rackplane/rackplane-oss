"""add vertical column to catalog_skus

Revision ID: add_catalog_vertical
Revises: merge_whitelabel_cart
Create Date: 2024-12-25

Adds 'vertical' column to catalog_skus table for industry vertical filtering.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

# Import idempotency helpers per GEMINI.md
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alembic_helpers import index_exists, column_exists

# revision identifiers, used by Alembic.
revision: str = 'add_catalog_vertical'
down_revision: Union[str, None] = 'merge_whitelabel_cart'  # Correct parent revision
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vertical column to catalog_skus with default 'datacenter'."""
    conn = op.get_bind()
    
    # Check if column already exists (idempotent)
    if not column_exists(conn, 'catalog_skus', 'vertical'):
        op.add_column('catalog_skus', 
            sa.Column('vertical', sa.String(50), 
                     server_default='datacenter', 
                     nullable=True,
                     comment='Industry vertical (datacenter, healthcare, warehouse)')
        )
        
        # Update existing rows to datacenter
        op.execute("UPDATE catalog_skus SET vertical = 'datacenter' WHERE vertical IS NULL")
    
    # Create index if not exists (idempotent)
    if not index_exists(conn, 'ix_catalog_skus_vertical'):
        try:
            op.create_index('ix_catalog_skus_vertical', 'catalog_skus', ['vertical'])
        except (OperationalError, ProgrammingError) as e:
            # Only ignore if index already exists
            if 'already exists' in str(e).lower():
                pass
            else:
                raise


def downgrade() -> None:
    """Remove vertical column from catalog_skus."""
    conn = op.get_bind()
    
    # Drop index if exists
    if index_exists(conn, 'ix_catalog_skus_vertical'):
        try:
            op.drop_index('ix_catalog_skus_vertical', 'catalog_skus')
        except (OperationalError, ProgrammingError) as e:
            if 'does not exist' in str(e).lower():
                pass
            else:
                raise
    
    # Drop column if exists
    if column_exists(conn, 'catalog_skus', 'vertical'):
        op.drop_column('catalog_skus', 'vertical')

