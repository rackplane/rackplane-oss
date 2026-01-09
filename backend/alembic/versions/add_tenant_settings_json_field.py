"""add_tenant_settings_json_field

Revision ID: add_tenant_settings
Revises: add_rackplane_subscription_fields
Create Date: 2025-12-02 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_tenant_settings'
down_revision: Union[str, Sequence[str], None] = 'add_rackplane_subscription'  # Match the actual revision ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' in table_names:
        columns = [col['name'] for col in inspector.get_columns('tenants')]

        if 'tenant_settings' not in columns:
            op.add_column('tenants', sa.Column('tenant_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, 
                server_default=sa.text("'{\"show_dev_troubleshooting\": false, \"enable_debug_logs\": false}'::jsonb"), 
                comment='Tenant-wide settings (UI preferences, feature flags, etc.)'))
            # Set default for existing tenants
            op.execute("""
                UPDATE tenants 
                SET tenant_settings = '{"show_dev_troubleshooting": false, "enable_debug_logs": false}'::jsonb 
                WHERE tenant_settings IS NULL
            """)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if 'tenants' in table_names:
        columns = [col['name'] for col in inspector.get_columns('tenants')]

        if 'tenant_settings' in columns:
            op.drop_column('tenants', 'tenant_settings')

