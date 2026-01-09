"""merge_stripe_and_prior

Revision ID: 0c530a5e0d19
Revises: add_stripe_fields, e4316bf57e1e
Create Date: 2025-12-09 00:54:48.087180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c530a5e0d19'
down_revision: Union[str, None] = ('add_stripe_fields', 'e4316bf57e1e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

