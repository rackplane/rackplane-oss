"""increase_rackplane_api_key_size_for_jwt_tokens

Revision ID: fcb58769b19c
Revises: add_ocr_scans
Create Date: 2025-12-10 19:26:06.836710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcb58769b19c'
down_revision: Union[str, None] = 'add_ocr_scans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Increase rackplane_api_key column size from String(255) to Text.
    
    JWT license tokens can be 600+ characters, so we need a larger column.
    """
    from sqlalchemy import inspect
    
    # Check if column exists
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col['name']: col for col in inspector.get_columns('tenants')}
    
    if 'rackplane_api_key' in columns:
        # Use direct SQL to change column type with explicit casting for PostgreSQL
        # The USING clause ensures safe type conversion from VARCHAR(255) to TEXT
        op.execute(
            "ALTER TABLE tenants ALTER COLUMN rackplane_api_key TYPE TEXT USING rackplane_api_key::text"
        )


def downgrade() -> None:
    """
    Revert rackplane_api_key column back to String(255).
    
    WARNING: This will truncate any tokens longer than 255 characters.
    """
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col['name']: col for col in inspector.get_columns('tenants')}
    
    if 'rackplane_api_key' in columns:
        # Use direct SQL with explicit casting for PostgreSQL
        # The USING clause ensures safe type conversion from TEXT to VARCHAR(255)
        # Note: Values longer than 255 characters will be truncated
        op.execute(
            "ALTER TABLE tenants ALTER COLUMN rackplane_api_key TYPE VARCHAR(255) USING rackplane_api_key::varchar(255)"
        )

