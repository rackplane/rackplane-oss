"""merge tenant uuid and catalog submissions heads

Revision ID: 7ffbf37eab0c
Revises: add_tenant_uuid, fb931faace47
Create Date: 2026-01-02 20:31:50.043273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ffbf37eab0c'
down_revision: Union[str, None] = ('add_tenant_uuid', 'fb931faace47')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

