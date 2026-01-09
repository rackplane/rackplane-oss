"""fix missing columns

Revision ID: fix_missing_cols
Revises: fcb58769b19c
Create Date: 2025-12-11 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_missing_cols'
down_revision = 'fcb58769b19c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Fix Tenants table (add missing columns)
    if 'tenants' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('tenants')]
        
        if 'subscription_features' not in columns:
            op.add_column('tenants', 
                sa.Column('subscription_features', postgresql.JSON(astext_type=sa.Text()), 
                         nullable=True, 
                         server_default='{}',
                         comment='Enabled commercial features (ocr_cloud, vendor_lookup, etc.)')
            )
            
        if 'rackplane_api_key' not in columns:
            op.add_column('tenants',
                sa.Column('rackplane_api_key', sa.Text(), 
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
                         
        if 'tenant_settings' not in columns:
             op.add_column('tenants', sa.Column('tenant_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, 
                server_default=sa.text("'{\"show_dev_troubleshooting\": false, \"enable_debug_logs\": false}'::jsonb"),
                comment='Tenant-wide settings (UI preferences, feature flags, etc.)'))

    # 2. Fix Vendor SKUs table (safely create if completely missing)
    if 'vendor_skus' not in inspector.get_table_names():
        op.create_table(
            'vendor_skus',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vendor', sa.String(length=100), nullable=False),
            sa.Column('sku', sa.String(length=200), nullable=False),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('asset_type', sa.String(length=100), nullable=True),
            sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('price_usd', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=True, server_default='USD'),
            sa.Column('price_updated_at', sa.DateTime(), nullable=True),
            sa.Column('compatibility', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('datasheet_url', sa.String(length=500), nullable=True),
            sa.Column('vendor_url', sa.String(length=500), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('last_verified', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        # Create indexes only if we created the table
        op.create_index(op.f('ix_vendor_skus_id'), 'vendor_skus', ['id'], unique=False)
        op.create_index(op.f('ix_vendor_skus_vendor'), 'vendor_skus', ['vendor'], unique=False)
        op.create_index(op.f('ix_vendor_skus_sku'), 'vendor_skus', ['sku'], unique=False)
        op.create_index('ix_vendor_sku_vendor_sku', 'vendor_skus', ['vendor', 'sku'], unique=False)


def downgrade() -> None:
    # Downgrade logic to remove these columns if needed
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'tenants' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('tenants')]
        
        if 'tenant_settings' in columns:
            op.drop_column('tenants', 'tenant_settings')
            
        if 'rackplane_api_key_hash' in columns:
            op.drop_column('tenants', 'rackplane_api_key_hash')
            
        if 'rackplane_api_key' in columns:
            op.drop_column('tenants', 'rackplane_api_key')
            
        if 'subscription_features' in columns:
            op.drop_column('tenants', 'subscription_features')
    
    # Do NOT drop vendor_skus in downgrade because it might have existed before
