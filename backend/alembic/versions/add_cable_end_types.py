"""add cable connector ends

Revision ID: add_cable_end_types
Revises: add_lane_encoding, 38a1de17fa66
Create Date: 2025-12-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy import text
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision = 'add_cable_end_types'
down_revision: Union[str, Sequence[str]] = ('add_lane_encoding', '38a1de17fa66')
branch_labels = None
depends_on = None

def upgrade() -> None:
    from alembic import util
    conn = op.get_bind()
    
    # Debug: Print current user and search path
    user_info = conn.execute(text("SELECT current_user, current_schemas(true)")).fetchone()
    util.status(f"Migration context: user={user_info[0]}, schemas={user_info[1]}")

    # 1. Update Enum values (Postgres)
    # Check if connectortype enum exists
    result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'connectortype'"))
    if result.fetchone():
        util.status("Updating connectortype enum values...")
        op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'sfp28'")
        op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'qsfp56'")
        op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'osfp-fin'")
        op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'osfp-flt'")

    # 2. Add columns to network_cables using robust Postgres syntax
    # First, ensure the table exists (it should, but let's be safe)
    result = conn.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'network_cables'"))
    if not result.fetchone():
        util.status("WARNING: network_cables table not found in information_schema! Tables available: " + 
                    str([row[0] for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog')")).fetchall()]))
    
    util.status("Ensuring connector_type_end_a/b columns exist in network_cables...")
    
    # Postgres 9.6+ supports ADD COLUMN IF NOT EXISTS
    op.execute("ALTER TABLE network_cables ADD COLUMN IF NOT EXISTS connector_type_end_a VARCHAR(50)")
    op.execute("ALTER TABLE network_cables ADD COLUMN IF NOT EXISTS connector_type_end_b VARCHAR(50)")
    
    # Create indexes if they don't exist
    # Note: Postgres doesn't have CREATE INDEX IF NOT EXISTS in old versions, but 9.5+ does
    op.execute("CREATE INDEX IF NOT EXISTS ix_network_cables_connector_type_end_a ON network_cables (connector_type_end_a)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_network_cables_connector_type_end_b ON network_cables (connector_type_end_b)")
    
    util.status("✓ Cable end type columns verified/added.")

def downgrade() -> None:
    # Remove columns
    op.drop_index('ix_network_cables_connector_type_end_b', table_name='network_cables')
    op.drop_column('network_cables', 'connector_type_end_b')
    op.drop_index('ix_network_cables_connector_type_end_a', table_name='network_cables')
    op.drop_column('network_cables', 'connector_type_end_a')
