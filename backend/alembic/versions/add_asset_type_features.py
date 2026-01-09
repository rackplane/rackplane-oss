"""Add features JSONB column to asset_types

Revision ID: add_asset_type_features
Revises: merge_catalog_vertical_heads
Create Date: 2025-12-26

Adds a JSONB 'features' column to asset_types table for flexible capability flags.
Sets default 'networkable' flag for known networking device types.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import sys
import os
# Add alembic directory to path for alembic_helpers import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from alembic_helpers import column_exists

# revision identifiers
revision = 'add_asset_type_features'
down_revision = 'merge_catalog_vertical_heads'
branch_labels = None
depends_on = None

# Asset types that should have networkable=True by default
NETWORKABLE_TYPES = [
    'server', 'switch', 'router', 'firewall', 'pdu', 'ups',
    'storage', 'san', 'nas', 'appliance', 'enclosure', 'blade',
    'patch_panel', 'console_server', 'kvm', 'network_switch'
]


def upgrade():
    conn = op.get_bind()
    
    # Add column if not exists
    if not column_exists(conn, 'asset_types', 'features'):
        op.add_column('asset_types', sa.Column(
            'features', JSONB, nullable=False, server_default='{}'
        ))
    
    # Set networkable=True for known device types
    for asset_type in NETWORKABLE_TYPES:
        conn.execute(sa.text("""
            UPDATE asset_types 
            SET features = jsonb_set(COALESCE(features, '{}'), '{networkable}', 'true')
            WHERE LOWER(name) LIKE :pattern
            AND (features IS NULL OR NOT (features ? 'networkable'))
        """), {"pattern": f"%{asset_type}%"})


def downgrade():
    conn = op.get_bind()
    if column_exists(conn, 'asset_types', 'features'):
        op.drop_column('asset_types', 'features')
