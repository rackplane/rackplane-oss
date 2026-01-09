"""add_environments_table

Revision ID: 30805a5e63dc
Revises: fix_incorrect_stock_thresholds, cff3b4de952b
Create Date: 2025-11-28 21:37:38.391511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30805a5e63dc'
down_revision: Union[str, Sequence[str], None] = ('fix_incorrect_stock_thresholds', 'cff3b4de952b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create environments table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'environments' not in existing_tables:
        op.create_table(
            'environments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('ssh_link', sa.String(length=200), nullable=False),
            sa.Column('ipmi_link', sa.String(length=200), nullable=False),
            sa.Column('ssh_username', sa.String(length=100), nullable=True),
            sa.Column('ssh_password', sa.String(length=200), nullable=True),
            sa.Column('ipmi_username', sa.String(length=100), nullable=True),
            sa.Column('ipmi_password', sa.String(length=200), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_environments_id'), 'environments', ['id'], unique=False)
        op.create_index(op.f('ix_environments_name'), 'environments', ['name'], unique=False)
        op.create_index(op.f('ix_environments_tenant_id'), 'environments', ['tenant_id'], unique=False)
    else:
        # Table already exists, just ensure indexes exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('environments')]
        if 'ix_environments_id' not in existing_indexes:
            op.create_index(op.f('ix_environments_id'), 'environments', ['id'], unique=False)
        if 'ix_environments_name' not in existing_indexes:
            op.create_index(op.f('ix_environments_name'), 'environments', ['name'], unique=False)
        if 'ix_environments_tenant_id' not in existing_indexes:
            op.create_index(op.f('ix_environments_tenant_id'), 'environments', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_environments_tenant_id'), table_name='environments')
    op.drop_index(op.f('ix_environments_name'), table_name='environments')
    op.drop_index(op.f('ix_environments_id'), table_name='environments')
    op.drop_table('environments')

