"""add plugin config and vertical pack index

Revision ID: add_plugin_config
Revises: add_whitelabel_config
Create Date: 2025-12-24

Adds:
- plugin_config: JSON Store for plugin configurations
- index on vertical_pack for faster filtering
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json


# revision identifiers, used by Alembic.
revision: str = 'add_plugin_config'
down_revision: Union[str, Sequence[str], None] = 'add_whitelabel_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add plugin_config column and vertical_pack index"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' not in table_names:
        return

    columns = [col['name'] for col in inspector.get_columns('tenants')]
    indexes = [idx['name'] for idx in inspector.get_indexes('tenants')]

    # Add plugin_config column
    if 'plugin_config' not in columns:
        op.add_column('tenants', sa.Column(
            'plugin_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Per-tenant plugin configuration and enablement state'
        ))
        
        # Set default safely using sqlalchemy parameters
        default_config = json.dumps({"plugins": []})
        op.execute(
            sa.text("UPDATE tenants SET plugin_config = :val ::jsonb WHERE plugin_config IS NULL")
            .bindparams(val=default_config)
        )

    # Add index for vertical_pack (if column exists)
    if 'vertical_pack' in columns:
        # Check if index already exists (avoid duplicates)
        has_index = False
        for idx in inspector.get_indexes('tenants'):
            if idx['column_names'] == ['vertical_pack']:
                has_index = True
                break
        
        if not has_index:
            op.create_index(
                op.f('ix_tenants_vertical_pack'), 
                'tenants', 
                ['vertical_pack'], 
                unique=False
            )


def downgrade() -> None:
    """Remove plugin_config column and index"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' not in table_names:
        return

    columns = [col['name'] for col in inspector.get_columns('tenants')]

    if 'plugin_config' in columns:
        op.drop_column('tenants', 'plugin_config')
    
    # Check for index before dropping
    # Note: drop_column usually drops dependent indexes, but explicit is fine
    op.drop_index(op.f('ix_tenants_vertical_pack'), table_name='tenants')
