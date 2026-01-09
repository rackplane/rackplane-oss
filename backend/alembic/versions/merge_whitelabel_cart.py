"""merge whitelabel and shopping cart heads

Revision ID: merge_whitelabel_cart
Revises: 535df0b78c56, 903c3fe96d65
Create Date: 2025-12-24 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_whitelabel_cart'
down_revision: Union[str, Sequence[str], None] = ('535df0b78c56', '903c3fe96d65')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
