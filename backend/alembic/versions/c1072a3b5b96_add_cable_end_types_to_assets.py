"""add cable end types to assets

Revision ID: c1072a3b5b96
Revises: merge_all_migration_heads
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1072a3b5b96'
down_revision = 'merge_all_migration_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Robust check for columns in assets table
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    if 'connector_type_end_a' not in columns:
        op.add_column('assets', sa.Column('connector_type_end_a', sa.String(length=50), nullable=True))
        op.create_index(op.f('ix_assets_connector_type_end_a'), 'assets', ['connector_type_end_a'], unique=False)
        
    if 'connector_type_end_b' not in columns:
        op.add_column('assets', sa.Column('connector_type_end_b', sa.String(length=50), nullable=True))
        op.create_index(op.f('ix_assets_connector_type_end_b'), 'assets', ['connector_type_end_b'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]

    if 'connector_type_end_b' in columns:
        op.drop_index(op.f('ix_assets_connector_type_end_b'), table_name='assets')
        op.drop_column('assets', 'connector_type_end_b')
    if 'connector_type_end_a' in columns:
        op.drop_index(op.f('ix_assets_connector_type_end_a'), table_name='assets')
        op.drop_column('assets', 'connector_type_end_a')
