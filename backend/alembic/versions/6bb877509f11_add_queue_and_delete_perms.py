"""add queue and delete perms

Revision ID: 6bb877509f11
Revises: 73c1a2cbd8b2
Create Date: 2026-01-01 20:42:41.389999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb877509f11'
down_revision: Union[str, None] = '73c1a2cbd8b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy import inspect

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('api_customers')]

    if 'can_contribute' not in columns:
        op.add_column('api_customers', sa.Column('can_contribute', sa.Boolean(), nullable=True, comment='Permission to submit SKUs to the central pending queue'))
    
    if 'can_delete_skus' not in columns:
        op.add_column('api_customers', sa.Column('can_delete_skus', sa.Boolean(), nullable=True, comment='Permission to delete SKUs from central catalog'))


def downgrade() -> None:
    op.drop_column('api_customers', 'can_delete_skus')
    op.drop_column('api_customers', 'can_contribute')

