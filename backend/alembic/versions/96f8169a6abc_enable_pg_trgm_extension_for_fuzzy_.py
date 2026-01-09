"""enable pg_trgm extension for fuzzy search

Revision ID: 96f8169a6abc
Revises: ffd4bd8c3932
Create Date: 2025-12-21 01:23:58.720288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96f8169a6abc'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'  # Updated to depend on cable_assemblies migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy text matching in asset search
    # This enables the % operator for similarity matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    # Drop pg_trgm extension
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

