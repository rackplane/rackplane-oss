"""merge_tenant_settings_head

Revision ID: 0b8dcffbf433
Revises: 9daf23dd4c1a, add_tenant_settings
Create Date: 2025-12-02 18:17:14.353766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b8dcffbf433'
down_revision: Union[str, None] = ('9daf23dd4c1a', 'add_tenant_settings')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

