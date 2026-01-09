"""Update tenant_id column size from 100 to 36 characters

Revision ID: update_tenant_id_size
Revises: 7ffbf37eab0c
Create Date: 2026-01-02 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'update_tenant_id_size'
down_revision = '7ffbf37eab0c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Update api_customers.tenant_id from VARCHAR(100) to VARCHAR(36).
    UUIDs are always 36 characters, so this is a safe size reduction.
    """
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    if 'api_customers' not in inspector.get_table_names():
        return

    # Check if column exists
    columns = {c['name']: c for c in inspector.get_columns('api_customers')}
    if 'tenant_id' not in columns:
        return

    # Alter column type to VARCHAR(36)
    op.alter_column('api_customers', 'tenant_id',
                    type_=sa.String(36),
                    existing_type=sa.String(100),
                    existing_nullable=True,
                    existing_comment='Tenant UUID from Tenant.uuid for contribution credit tracking')


def downgrade() -> None:
    """Revert tenant_id back to VARCHAR(100)."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'api_customers' not in inspector.get_table_names():
        return

    columns = {c['name']: c for c in inspector.get_columns('api_customers')}
    if 'tenant_id' not in columns:
        return

    op.alter_column('api_customers', 'tenant_id',
                    type_=sa.String(100),
                    existing_type=sa.String(36),
                    existing_nullable=True)
