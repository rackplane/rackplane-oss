"""add_user_role_column

Revision ID: add_user_role_column
Revises: 30805a5e63dc
Create Date: 2025-11-29 07:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_user_role_column'
down_revision: Union[str, None] = '30805a5e63dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if userrole enum exists and has correct values
    result = conn.execute(sa.text("""
        SELECT typname FROM pg_type WHERE typname = 'userrole'
    """))
    enum_exists = result.fetchone() is not None
    
    if enum_exists:
        # Check enum values
        result = conn.execute(sa.text("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
            ORDER BY enumsortorder
        """))
        enum_values = [row[0] for row in result.fetchall()]
        
        # If enum has uppercase values, drop and recreate with lowercase
        if enum_values and enum_values[0].isupper():
            op.execute("DROP TYPE IF EXISTS userrole CASCADE")
            op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'tenant_admin', 'user', 'read_only')")
    else:
        op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'tenant_admin', 'user', 'read_only')")
    
    # Check if role column exists, add if not
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'role' not in columns:
        op.add_column('users', sa.Column('role', sa.Enum('super_admin', 'tenant_admin', 'user', 'read_only', name='userrole'), nullable=False, server_default='user'))
    
    # Check if index exists, create if not
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_role' not in indexes:
        op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    
    # Update existing users: if is_super_admin is True, set role to super_admin
    op.execute("UPDATE users SET role = 'super_admin' WHERE is_super_admin = true AND (role IS NULL OR role = 'user')")
    
    # Update existing users: if is_super_admin is False and role is still default, keep as 'user'
    # (This is already handled by the default, but we'll be explicit)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_users_role'), table_name='users')
    
    # Drop role column
    op.drop_column('users', 'role')
    
    # Drop enum type
    op.execute("DROP TYPE userrole")

