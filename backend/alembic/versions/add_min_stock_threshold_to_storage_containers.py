"""add min_stock_threshold to storage_containers

Revision ID: add_min_stock_threshold_sc
Revises: 
Create Date: 2024-11-29 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_min_stock_threshold_sc'
down_revision = 'add_audit_logs_table'  # Set to the current head
branch_labels = None
depends_on = None


def upgrade():
    # Add min_stock_threshold column to storage_containers table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('storage_containers')]
    
    if 'min_stock_threshold' not in columns:
        op.add_column('storage_containers', sa.Column('min_stock_threshold', sa.Integer(), nullable=True, server_default='0', comment='Minimum stock level for reorder alerts'))


def downgrade():
    # Remove min_stock_threshold column from storage_containers table
    op.drop_column('storage_containers', 'min_stock_threshold')

