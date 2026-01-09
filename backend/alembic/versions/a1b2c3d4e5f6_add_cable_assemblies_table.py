"""add_cable_assemblies_table

Revision ID: a1b2c3d4e5f6
Revises: ffd4bd8c3932
Create Date: 2024-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'ffd4bd8c3932'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cable_assemblies table (idempotent)"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Check if table already exists
    if 'cable_assemblies' not in inspector.get_table_names():
        op.create_table(
            'cable_assemblies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('fiber_cable_id', sa.Integer(), nullable=False),
            sa.Column('transceiver_a_id', sa.Integer(), nullable=False),
            sa.Column('transceiver_b_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.Enum('available', 'deployed', 'reserved', 'maintenance', name='assemblystatus'), nullable=False, server_default='available'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['fiber_cable_id'], ['assets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['transceiver_a_id'], ['assets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['transceiver_b_id'], ['assets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_cable_assemblies_id'), 'cable_assemblies', ['id'], unique=False)
        op.create_index(op.f('ix_cable_assemblies_name'), 'cable_assemblies', ['name'], unique=False)
        op.create_index(op.f('ix_cable_assemblies_tenant_id'), 'cable_assemblies', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Drop cable_assemblies table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if 'cable_assemblies' in inspector.get_table_names():
        op.drop_index(op.f('ix_cable_assemblies_tenant_id'), table_name='cable_assemblies')
        op.drop_index(op.f('ix_cable_assemblies_name'), table_name='cable_assemblies')
        op.drop_index(op.f('ix_cable_assemblies_id'), table_name='cable_assemblies')
        op.drop_table('cable_assemblies')
    
    # Drop enum type if exists
    try:
        op.execute('DROP TYPE IF EXISTS assemblystatus')
    except Exception:
        pass
