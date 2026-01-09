# Copyright (c) 2024 RackPlane <info@rackplane.com>
"""Add tenant_id and api_key_plain to ApiCustomer

Revision ID: add_api_customer_tenant_id
Revises: add_global_product_catalog
Create Date: 2025-12-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = 'add_api_customer_tenant_id'
down_revision = 'add_global_cat'
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant_id and api_key_plain columns to api_customers table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Check if table exists
    tables = inspector.get_table_names()
    if 'api_customers' not in tables:
        # Table doesn't exist - it will be created by the initial migration
        return
    
    # Get existing columns
    columns = [c['name'] for c in inspector.get_columns('api_customers')]
    
    # Add tenant_id if not exists
    if 'tenant_id' not in columns:
        op.add_column('api_customers', sa.Column(
            'tenant_id', sa.String(36), nullable=True,
            comment='Tenant UUID from Tenant.uuid for contribution credit tracking'
        ))
        op.create_index('ix_api_customers_tenant_id', 'api_customers', ['tenant_id'])
    
    # Add api_key_plain if not exists
    if 'api_key_plain' not in columns:
        op.add_column('api_customers', sa.Column(
            'api_key_plain', sa.String(100), nullable=True,
            comment='Temporary storage of plain API key for display'
        ))


def downgrade():
    """Remove tenant_id and api_key_plain from api_customers table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    tables = inspector.get_table_names()
    if 'api_customers' not in tables:
        return
    
    columns = [c['name'] for c in inspector.get_columns('api_customers')]
    
    if 'tenant_id' in columns:
        op.drop_index('ix_api_customers_tenant_id', table_name='api_customers')
        op.drop_column('api_customers', 'tenant_id')
    
    if 'api_key_plain' in columns:
        op.drop_column('api_customers', 'api_key_plain')
