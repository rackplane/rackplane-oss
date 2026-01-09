"""add_super_admin_field

Revision ID: 7656f9a6dc2a
Revises: 001_add_multi_tenancy
Create Date: 2025-11-21 00:19:10.511828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7656f9a6dc2a'
down_revision: Union[str, None] = '001_add_multi_tenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_super_admin column to users table
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if column already exists
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'is_super_admin' not in columns:
            op.add_column('users', sa.Column('is_super_admin', sa.Boolean(), nullable=False, server_default='false'))
            op.create_index('ix_users_is_super_admin', 'users', ['is_super_admin'], unique=False)
            
            # Make the default admin user (admin) a super admin
            op.execute(sa.text("""
                UPDATE users 
                SET is_super_admin = true 
                WHERE username = 'admin'
            """))


def downgrade() -> None:
    # Remove is_super_admin column
    op.drop_index('ix_users_is_super_admin', table_name='users')
    op.drop_column('users', 'is_super_admin')

