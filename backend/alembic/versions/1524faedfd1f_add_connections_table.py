"""add_connections_table

Revision ID: 1524faedfd1f
Revises: 7656f9a6dc2a
Create Date: 2025-11-21 05:48:04.804917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1524faedfd1f'
down_revision: Union[str, None] = '7656f9a6dc2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Create connections table if it doesn't exist
    # Only create if assets table exists (required for foreign keys)
    if 'connections' not in inspector.get_table_names():
        # Check if assets table exists before creating foreign keys
        tables = inspector.get_table_names()
        has_assets = 'assets' in tables
        has_tenants = 'tenants' in tables
        
        if not has_assets or not has_tenants:
            # Skip creating connections table if required tables don't exist
            # This can happen in fresh databases where base tables haven't been created yet
            return
        
        op.create_table(
            'connections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cable_asset_id', sa.Integer(), nullable=False),
            sa.Column('device_asset_id', sa.Integer(), nullable=False),
            sa.Column('port_label', sa.String(length=100), nullable=True),
            sa.Column('end_label', sa.Enum('A', 'B', name='connectionend'), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['cable_asset_id'], ['assets.id'], ),
            sa.ForeignKeyConstraint(['device_asset_id'], ['assets.id'], ),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('cable_asset_id', 'end_label', name='uq_cable_end')
        )
        op.create_index('ix_connections_id', 'connections', ['id'], unique=False)
        op.create_index('ix_connections_cable_asset_id', 'connections', ['cable_asset_id'], unique=False)
        op.create_index('ix_connections_device_asset_id', 'connections', ['device_asset_id'], unique=False)
        op.create_index('ix_connections_tenant_id', 'connections', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_connections_tenant_id', table_name='connections')
    op.drop_index('ix_connections_device_asset_id', table_name='connections')
    op.drop_index('ix_connections_cable_asset_id', table_name='connections')
    op.drop_index('ix_connections_id', table_name='connections')
    op.drop_table('connections')
    op.execute("DROP TYPE IF EXISTS connectionend")

