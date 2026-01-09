"""merge_all_heads

Revision ID: 38a1de17fa66
Revises: add_vendor_skus
Create Date: 2025-12-01 00:10:19.376309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38a1de17fa66'
down_revision: Union[str, Sequence[str], None] = ('35e712b2750f', '488be11bdfb4', 'add_email_notif_prefs', 'add_vendor_skus')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

