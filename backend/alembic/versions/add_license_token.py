"""Add license_token to tenants

Revision ID: add_license_token
Revises: 
Create Date: 2024-12-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_license_token'
down_revision = None  # Set this to the latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add license_token column to tenants table."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if tenants table exists
    if 'tenants' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('tenants')]
        
        # Add license_token column if it doesn't exist
        if 'license_token' not in columns:
            op.add_column('tenants', 
                sa.Column('license_token', sa.Text(), nullable=True,
                         comment='JWT license token for local premium features'))


def downgrade() -> None:
    """Remove license_token column from tenants table."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'tenants' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('tenants')]
        if 'license_token' in columns:
            op.drop_column('tenants', 'license_token')
