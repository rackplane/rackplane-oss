"""add_scopes_to_api_keys

Revision ID: 9daf23dd4c1a
Revises: 9bdcb39ba354
Create Date: 2025-12-01 21:38:44.298305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9daf23dd4c1a'
down_revision: Union[str, None] = '9bdcb39ba354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add scopes column to api_keys table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('api_keys')]
    if 'scopes' not in columns:
        op.add_column('api_keys', sa.Column('scopes', sa.JSON(), nullable=True, comment="List of allowed scopes. Empty list or None = all scopes"))


def downgrade() -> None:
    # Remove scopes column
    op.drop_column('api_keys', 'scopes')

