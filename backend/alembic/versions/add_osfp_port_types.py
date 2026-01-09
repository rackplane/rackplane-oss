"""Add OSFP and QSFP112 to PortType enum

Revision ID: add_osfp_port_types
Revises: migrate_connections_to_ports
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_osfp_port_types'
down_revision = 'migrate_connections_to_ports'
branch_labels = None
depends_on = None


def upgrade():
    """Add OSFP, QSFP112, OSFP_FIN and OSFP_FLT to the porttype enum."""
    # PostgreSQL enum values must be added with ALTER TYPE
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'qsfp112'")
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'osfp'")
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'osfp_fin'")
    op.execute("ALTER TYPE porttype ADD VALUE IF NOT EXISTS 'osfp_flt'")


def downgrade():
    """
    Note: PostgreSQL doesn't support removing values from enums easily.
    To fully downgrade, you'd need to:
    1. Create a new enum without these values
    2. Migrate all data
    3. Drop old enum and rename new one
    
    For simplicity, we leave the enum values in place on downgrade.
    """
    pass
