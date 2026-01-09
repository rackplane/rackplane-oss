"""add_api_keys_label_unique_constraint

Revision ID: 1864ebe8a518
Revises: c6ea09d24faf
Create Date: 2025-12-01 21:18:11.822109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1864ebe8a518'
down_revision: Union[str, None] = 'c6ea09d24faf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add unique constraint for API key labels per user per tenant.
    
    This prevents users from creating duplicate API key labels, which would
    cause confusion when managing multiple keys.
    
    Constraint: (user_id, label, tenant_id) must be unique
    """
    import sqlalchemy as sa
    from sqlalchemy import inspect
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if 'api_keys' in inspector.get_table_names():
        # Check if constraint already exists
        result = connection.execute(sa.text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'api_keys' AND indexname = 'idx_api_keys_user_label_tenant'
        """))
        exists = result.scalar() > 0
        
        if not exists:
            # Create unique index for (user_id, label, tenant_id)
            # This prevents duplicate labels for the same user within a tenant
            op.create_index(
                'idx_api_keys_user_label_tenant',
                'api_keys',
                ['user_id', 'label', 'tenant_id'],
                unique=True,
                postgresql_where=sa.text('label IS NOT NULL')
            )


def downgrade() -> None:
    """
    WARNING: This downgrade intentionally does NOT drop the constraint.
    
    This constraint is important for data integrity and should not be dropped.
    """
    # Intentionally empty - we do NOT want to drop this constraint
    pass

