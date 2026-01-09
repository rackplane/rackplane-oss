"""add sfp56 and qsfp56 types

Revision ID: add_sfp56_qsfp56
Revises: add_cable_end_types
Create Date: 2025-12-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
# revision identifiers, used by Alembic.
revision = 'add_sfp56_qsfp56'
down_revision = 'add_cable_end_types'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Postgres Enum update needs explicit SQL
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'SFP56'")
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'QSFP56'")

def downgrade() -> None:
    # Cannot easily drop enum value in Postgres
    pass
