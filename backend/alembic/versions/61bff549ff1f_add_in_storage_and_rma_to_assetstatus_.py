"""add_in_storage_and_rma_to_assetstatus_enum

Revision ID: 61bff549ff1f
Revises: 1b05f9f43610
Create Date: 2025-11-21 17:55:41.703770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61bff549ff1f'
down_revision: Union[str, None] = '1b05f9f43610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to assetstatus enum
    # PostgreSQL requires adding enum values one at a time
    # Note: Using lowercase to match existing enum values in database
    # Check if the enum type exists first (some databases use varchar instead)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'assetstatus'
        )
    """))
    enum_exists = result.scalar()
    
    if enum_exists:
        op.execute("ALTER TYPE assetstatus ADD VALUE IF NOT EXISTS 'in_storage'")
        op.execute("ALTER TYPE assetstatus ADD VALUE IF NOT EXISTS 'rma'")
        op.execute("ALTER TYPE assetstatus ADD VALUE IF NOT EXISTS 'retired'")
    else:
        # Enum doesn't exist - database likely uses varchar for status
        # This migration is not applicable
        pass


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # To downgrade, you would need to:
    # 1. Create a new enum without these values
    # 2. Update all columns to use the new enum
    # 3. Drop the old enum
    # This is complex and risky, so we'll leave a comment instead
    # For now, we'll just document that downgrade is not supported
    pass
    # raise NotImplementedError("Cannot remove enum values in PostgreSQL. Manual migration required.")

