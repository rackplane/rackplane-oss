"""add container_stock_thresholds table

Revision ID: add_container_stock_thresholds
Revises: add_min_stock_threshold_sc
Create Date: 2024-11-29 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_container_stock_thresholds'
down_revision = 'add_min_stock_threshold_sc'
branch_labels = None
depends_on = None


def upgrade():
    # Create container_stock_thresholds table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    if 'container_stock_thresholds' not in existing_tables:
        op.create_table(
            'container_stock_thresholds',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('storage_container_id', sa.Integer(), nullable=False),
            sa.Column('asset_type', sa.String(length=100), nullable=False),
            sa.Column('manufacturer', sa.String(length=100), nullable=True),
            sa.Column('model', sa.String(length=200), nullable=True),
            sa.Column('min_threshold', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['storage_container_id'], ['storage_containers.id'], ),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_container_stock_thresholds_storage_container_id'), 'container_stock_thresholds', ['storage_container_id'], unique=False)
        op.create_index(op.f('ix_container_stock_thresholds_asset_type'), 'container_stock_thresholds', ['asset_type'], unique=False)
        op.create_index(op.f('ix_container_stock_thresholds_manufacturer'), 'container_stock_thresholds', ['manufacturer'], unique=False)
        op.create_index(op.f('ix_container_stock_thresholds_model'), 'container_stock_thresholds', ['model'], unique=False)
        op.create_index(op.f('ix_container_stock_thresholds_tenant_id'), 'container_stock_thresholds', ['tenant_id'], unique=False)
        
        # Create unique constraint
        op.create_unique_constraint(
            'uq_container_stock_threshold',
            'container_stock_thresholds',
            ['storage_container_id', 'asset_type', 'manufacturer', 'model', 'tenant_id']
        )
    else:
        # Table exists, just ensure indexes and constraints exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('container_stock_thresholds')]
        if 'ix_container_stock_thresholds_storage_container_id' not in existing_indexes:
            op.create_index(op.f('ix_container_stock_thresholds_storage_container_id'), 'container_stock_thresholds', ['storage_container_id'], unique=False)
        if 'ix_container_stock_thresholds_asset_type' not in existing_indexes:
            op.create_index(op.f('ix_container_stock_thresholds_asset_type'), 'container_stock_thresholds', ['asset_type'], unique=False)
        if 'ix_container_stock_thresholds_manufacturer' not in existing_indexes:
            op.create_index(op.f('ix_container_stock_thresholds_manufacturer'), 'container_stock_thresholds', ['manufacturer'], unique=False)
        if 'ix_container_stock_thresholds_model' not in existing_indexes:
            op.create_index(op.f('ix_container_stock_thresholds_model'), 'container_stock_thresholds', ['model'], unique=False)
        if 'ix_container_stock_thresholds_tenant_id' not in existing_indexes:
            op.create_index(op.f('ix_container_stock_thresholds_tenant_id'), 'container_stock_thresholds', ['tenant_id'], unique=False)


def downgrade():
    op.drop_constraint('uq_container_stock_threshold', 'container_stock_thresholds', type_='unique')
    op.drop_index(op.f('ix_container_stock_thresholds_tenant_id'), table_name='container_stock_thresholds')
    op.drop_index(op.f('ix_container_stock_thresholds_model'), table_name='container_stock_thresholds')
    op.drop_index(op.f('ix_container_stock_thresholds_manufacturer'), table_name='container_stock_thresholds')
    op.drop_index(op.f('ix_container_stock_thresholds_asset_type'), table_name='container_stock_thresholds')
    op.drop_index(op.f('ix_container_stock_thresholds_storage_container_id'), table_name='container_stock_thresholds')
    op.drop_table('container_stock_thresholds')


