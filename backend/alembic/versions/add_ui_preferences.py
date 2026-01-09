"""add ui_preferences to users

Revision ID: add_ui_preferences
Revises: add_osfp_port_types
Create Date: 2024-12-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ui_preferences'
down_revision = 'add_osfp_port_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ui_preferences column to users table (idempotent)
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'ui_preferences' not in columns:
        op.add_column('users', sa.Column('ui_preferences', sa.JSON(), nullable=True,
            comment='UI preferences (nav bar layout, theme, etc.)'))


def downgrade() -> None:
    op.drop_column('users', 'ui_preferences')
