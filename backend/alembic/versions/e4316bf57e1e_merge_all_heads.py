"""merge_all_heads

Revision ID: e4316bf57e1e
Revises: 4a3b1c2d5e6f, add_license_token
Create Date: 2025-12-08 08:00:26.825116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4316bf57e1e'
down_revision: Union[str, None] = ('4a3b1c2d5e6f', 'add_license_token')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

