"""ensure_tenant_0_for_sample_data

Revision ID: d14b4938e66b
Revises: df6126aa906d
Create Date: 2025-12-04 23:24:40.733322

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd14b4938e66b'
down_revision: Union[str, None] = 'df6126aa906d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ensure tenant_id=0 exists for RackPlane sample data.
    This tenant is used for sample/preview SKUs (is_sample=True, tenant_id=0).
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'tenants' in inspector.get_table_names():
        # Check if tenant_id=0 already exists
        result = conn.execute(sa.text("SELECT id FROM tenants WHERE id = 0")).fetchone()
        
        if not result:
            # Create tenant_id=0 for RackPlane sample data
            # Use op.execute to ensure proper transaction handling
            # Generate a fixed UUID for tenant 0 (deterministic for consistency)
            tenant_0_uuid = str(uuid.UUID('00000000-0000-0000-0000-000000000000'))

            op.execute(sa.text("""
                INSERT INTO tenants (
                    id, uuid, name, slug, is_active, subscription_tier,
                    subscription_features, tenant_settings, created_at, updated_at
                ) VALUES (
                    0,
                    :uuid,
                    'RackPlane Sample Data',
                    'rackplane-sample-data',
                    true,
                    'standard',
                    '{}',
                    '{"show_dev_troubleshooting": false, "enable_debug_logs": false}',
                    NOW(),
                    NOW()
                )
            """).bindparams(uuid=tenant_0_uuid))


def downgrade() -> None:
    """
    Remove tenant_id=0 (optional - may want to keep it for data integrity).
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'tenants' in inspector.get_table_names():
        # Check if tenant_id=0 exists
        result = conn.execute(sa.text("SELECT id FROM tenants WHERE id = 0")).fetchone()
        
        if result:
            # Only delete if no sample SKUs reference it (safety check)
            sku_count = conn.execute(sa.text("SELECT COUNT(*) FROM vendor_skus WHERE tenant_id = 0")).scalar()
            if sku_count == 0:
                conn.execute(sa.text("DELETE FROM tenants WHERE id = 0"))
                op.execute("COMMIT")
