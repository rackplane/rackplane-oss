"""add white-label configuration columns to tenants

Revision ID: add_whitelabel_config
Revises: merge_all_migration_heads
Create Date: 2025-12-24

Adds columns for white-label platform support:
- branding_config: Logo, colors, custom domain, fonts
- terminology: Configurable UI terminology (Asset -> Supply, etc.)
- vertical_pack: Which vertical pack is active (datacenter, healthcare, warehouse)
- vertical_features: Feature flags for vertical-specific features
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_whitelabel_config'
down_revision: Union[str, Sequence[str], None] = '96f8169a6abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default values for new columns
DEFAULT_BRANDING = {
    "name": None,
    "logo_url": None,
    "favicon_url": None,
    "primary_color": "#6366f1",
    "secondary_color": "#4f46e5",
    "accent_color": "#818cf8",
    "font_family": "Inter",
    "custom_domain": None,
    "email_from_name": None,
    "email_from_address": None
}

DEFAULT_TERMINOLOGY = {
    "item": "Asset",
    "items": "Assets",
    "location": "Datacenter",
    "locations": "Datacenters",
    "bin": "Rack",
    "bins": "Racks",
    "check_out": "Deploy",
    "check_in": "Return",
    "category": "Asset Type",
    "categories": "Asset Types",
    "lifecycle": "Status"
}

DEFAULT_VERTICAL_FEATURES = {
    "expiration_tracking": False,
    "par_levels": False,
    "lot_tracking": False,
    "department_attribution": False
}


def upgrade() -> None:
    """Add white-label configuration columns to tenants table."""
    import json
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' not in table_names:
        # Table doesn't exist yet - nothing to do
        return

    columns = [col['name'] for col in inspector.get_columns('tenants')]

    # Add branding_config column
    if 'branding_config' not in columns:
        op.add_column('tenants', sa.Column(
            'branding_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='White-label branding configuration (logo, colors, domain, etc.)'
        ))
        # Set default for existing tenants
        default_json = json.dumps(DEFAULT_BRANDING)
        op.execute(f"""
            UPDATE tenants 
            SET branding_config = '{default_json}'::jsonb 
            WHERE branding_config IS NULL
        """)

    # Add terminology column
    if 'terminology' not in columns:
        op.add_column('tenants', sa.Column(
            'terminology',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Configurable UI terminology (item->Supply, bin->Cabinet, etc.)'
        ))
        # Set default for existing tenants
        default_json = json.dumps(DEFAULT_TERMINOLOGY)
        op.execute(f"""
            UPDATE tenants 
            SET terminology = '{default_json}'::jsonb 
            WHERE terminology IS NULL
        """)

    # Add vertical_pack column
    if 'vertical_pack' not in columns:
        op.add_column('tenants', sa.Column(
            'vertical_pack',
            sa.String(50),
            nullable=True,
            server_default='datacenter',
            comment='Active vertical pack: datacenter, healthcare, warehouse'
        ))
        # Set default for existing tenants
        op.execute("""
            UPDATE tenants 
            SET vertical_pack = 'datacenter' 
            WHERE vertical_pack IS NULL
        """)

    # Add vertical_features column
    if 'vertical_features' not in columns:
        op.add_column('tenants', sa.Column(
            'vertical_features',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Vertical-specific feature flags (expiration_tracking, par_levels, etc.)'
        ))
        # Set default for existing tenants
        default_json = json.dumps(DEFAULT_VERTICAL_FEATURES)
        op.execute(f"""
            UPDATE tenants 
            SET vertical_features = '{default_json}'::jsonb 
            WHERE vertical_features IS NULL
        """)


def downgrade() -> None:
    """Remove white-label configuration columns from tenants table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' not in table_names:
        return

    columns = [col['name'] for col in inspector.get_columns('tenants')]

    if 'branding_config' in columns:
        op.drop_column('tenants', 'branding_config')

    if 'terminology' in columns:
        op.drop_column('tenants', 'terminology')

    if 'vertical_pack' in columns:
        op.drop_column('tenants', 'vertical_pack')

    if 'vertical_features' in columns:
        op.drop_column('tenants', 'vertical_features')
