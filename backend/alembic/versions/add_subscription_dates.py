# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""Add subscription renewal date tracking

Revision ID: add_subscription_dates
Revises: 
Create Date: 2025-12-15

Adds columns to track subscription renewal dates from Stripe:
- subscription_renewal_date: Next billing date from Stripe (current_period_end)
- subscription_grace_days: Days after renewal before expiration (default: 3)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_subscription_dates'
down_revision = 'add_api_customer_tenant_id'  # Link to existing migration chain
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add subscription renewal date columns to tenants table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    # Add subscription_renewal_date if not exists
    if 'subscription_renewal_date' not in columns:
        op.add_column('tenants', sa.Column(
            'subscription_renewal_date',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Next billing date from Stripe (current_period_end)'
        ))
    
    # Add subscription_grace_days if not exists
    if 'subscription_grace_days' not in columns:
        op.add_column('tenants', sa.Column(
            'subscription_grace_days',
            sa.Integer(),
            nullable=True,
            server_default='3',
            comment='Grace days after renewal date before online features expire'
        ))


def downgrade() -> None:
    """Remove subscription renewal date columns from tenants table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    if 'subscription_grace_days' in columns:
        op.drop_column('tenants', 'subscription_grace_days')
    
    if 'subscription_renewal_date' in columns:
        op.drop_column('tenants', 'subscription_renewal_date')
