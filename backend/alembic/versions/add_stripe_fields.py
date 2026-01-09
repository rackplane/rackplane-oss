"""Add Stripe billing fields to Tenant

Revision ID: add_stripe_fields
Revises: add_license_token
Create Date: 2024-12-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_stripe_fields'
down_revision = 'add_license_token'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('tenants')]

    if 'stripe_customer_id' not in columns:
        # Add Stripe customer ID
        op.add_column('tenants', sa.Column('stripe_customer_id', sa.String(255), nullable=True, 
                                            comment='Stripe Customer ID for billing'))
    
    if 'subscription_status' not in columns:
        # Add subscription status
        op.add_column('tenants', sa.Column('subscription_status', sa.String(50), nullable=True,
                                            server_default='demo',
                                            comment='Current subscription status: demo, active, past_due, cancelled'))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('tenants')]

    if 'subscription_status' in columns:
        op.drop_column('tenants', 'subscription_status')
    
    if 'stripe_customer_id' in columns:
        op.drop_column('tenants', 'stripe_customer_id')
