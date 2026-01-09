"""Add lane_encoding to network_ports

Revision ID: add_lane_encoding
Revises: add_ui_preferences
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_lane_encoding'
down_revision = 'add_ui_preferences'
branch_labels = None
depends_on = None


def upgrade():
    """Add lane_encoding enum and column to network_ports table."""
    # Create the enum type first
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE laneencoding AS ENUM ('nrz', 'pam4', 'both', 'unknown');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column with default value 'unknown'
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('network_ports')]
    if 'lane_encoding' not in columns:
        op.add_column(
            'network_ports',
            sa.Column('lane_encoding', sa.Enum('nrz', 'pam4', 'both', 'unknown', name='laneencoding'), 
                      nullable=True, server_default='unknown')
        )


def downgrade():
    """Remove lane_encoding column."""
    op.drop_column('network_ports', 'lane_encoding')
    # Note: We don't drop the enum type as it may cause issues if other tables use it
