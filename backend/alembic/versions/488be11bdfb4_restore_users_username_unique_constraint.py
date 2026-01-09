"""restore_users_username_unique_constraint

Revision ID: 488be11bdfb4
Revises: 0e3a451519ca
Create Date: 2025-11-30 20:07:56.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '488be11bdfb4'
down_revision: Union[str, Sequence[str], None] = '0e3a451519ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Restore unique constraint on users.username per tenant.
    
    This constraint was accidentally dropped in migration cff3b4de952b.
    The constraint ensures that usernames are unique within each tenant.
    """
    from sqlalchemy import inspect as sa_inspect
    
    connection = op.get_bind()
    inspector = sa_inspect(connection)
    
    # Check if the unique index already exists
    indexes = inspector.get_indexes('users')
    index_exists = any(
        idx['name'] == 'idx_users_username_tenant' and idx.get('unique', False)
        for idx in indexes
    )
    
    if not index_exists:
        # Check if there are any duplicate usernames per tenant
        # If so, we can't create the constraint until duplicates are cleaned up
        result = connection.execute(sa.text("""
            SELECT username, tenant_id, COUNT(*) as cnt
            FROM users
            GROUP BY username, tenant_id
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        if duplicates:
            total_duplicates = sum(dup[2] - 1 for dup in duplicates)
            raise Exception(
                f"Cannot create unique constraint: found {len(duplicates)} duplicate username(s) per tenant "
                f"({total_duplicates} total duplicate users). "
                f"Please run cleanup_duplicate_users.py or cleanup_production_duplicates.py --apply first."
            )
        
        # Create the unique index
        op.create_index(
            'idx_users_username_tenant',
            'users',
            ['username', 'tenant_id'],
            unique=True
        )
        print("✓ Created unique index idx_users_username_tenant on users(username, tenant_id)")
    else:
        print("✓ Unique index idx_users_username_tenant already exists")


def downgrade() -> None:
    """
    Drop the unique constraint on users.username per tenant.
    This reverses the upgrade and allows duplicate usernames again.
    """
    from sqlalchemy import inspect as sa_inspect
    
    connection = op.get_bind()
    inspector = sa_inspect(connection)
    
    # Check if the index exists
    indexes = inspector.get_indexes('users')
    index_exists = any(idx['name'] == 'idx_users_username_tenant' for idx in indexes)
    
    if index_exists:
        op.drop_index('idx_users_username_tenant', table_name='users')
        print("✓ Dropped unique index idx_users_username_tenant")
    else:
        print("✓ Unique index idx_users_username_tenant does not exist")
