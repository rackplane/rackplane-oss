"""add rackplane subscription fields

Revision ID: add_rackplane_subscription
Revises: 
Create Date: 2024-12-02

Adds subscription fields to tenants table for commercial features
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_rackplane_subscription'
down_revision = 'add_vendor_skus'  # Update to latest migration before this
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add subscription fields to tenants table.
    
    Adds:
    - subscription_features: JSON field with feature flags
    - rackplane_api_key: API key for RackPlane Services
    - rackplane_api_key_hash: Hashed API key (for security)
    """
    from sqlalchemy import inspect
    
    # Check if columns already exist (idempotency)
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    # Add subscription_features JSON field
    if 'subscription_features' not in columns:
        op.add_column('tenants', 
            sa.Column('subscription_features', postgresql.JSON(astext_type=sa.Text()), 
                     nullable=True, 
                     server_default='{}',
                     comment='Enabled commercial features (ocr_cloud, vendor_lookup, etc.)')
        )
    
    # Add API key fields
    if 'rackplane_api_key' not in columns:
        op.add_column('tenants',
            sa.Column('rackplane_api_key', sa.String(255), 
                     nullable=True, 
                     index=True,
                     comment='API key for RackPlane Services (commercial features)')
        )
    
    if 'rackplane_api_key_hash' not in columns:
        op.add_column('tenants',
            sa.Column('rackplane_api_key_hash', sa.String(255), 
                     nullable=True,
                     comment='Hashed API key for RackPlane Services (security)')
        )


def downgrade() -> None:
    """Remove subscription fields"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    if 'rackplane_api_key_hash' in columns:
        op.drop_column('tenants', 'rackplane_api_key_hash')
    
    if 'rackplane_api_key' in columns:
        op.drop_column('tenants', 'rackplane_api_key')
    
    if 'subscription_features' in columns:
        op.drop_column('tenants', 'subscription_features')

