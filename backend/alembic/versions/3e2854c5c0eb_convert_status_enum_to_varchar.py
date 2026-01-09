"""convert_status_enum_to_varchar

Revision ID: 3e2854c5c0eb
Revises: 61bff549ff1f
Create Date: 2025-11-21 18:53:38.208287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e2854c5c0eb'
down_revision: Union[str, None] = '61bff549ff1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert status column from enum to VARCHAR
    # This allows us to use enum values (lowercase) instead of enum names (uppercase)
    op.execute("""
        ALTER TABLE assets 
        ALTER COLUMN status TYPE VARCHAR(50) 
        USING status::text;
    """)


def downgrade() -> None:
    # Convert back to enum (this will fail if there are invalid values)
    # Note: This is a one-way migration in practice
    op.execute("""
        ALTER TABLE assets 
        ALTER COLUMN status TYPE assetstatus 
        USING status::assetstatus;
    """)

