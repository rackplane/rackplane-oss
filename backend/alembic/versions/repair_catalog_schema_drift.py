"""Repair catalog_skus schema drift

Revision ID: repair_catalog_drift
Revises: add_subscription_dates
Create Date: 2025-12-15 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'repair_catalog_drift'
down_revision = 'add_subscription_dates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'catalog_skus' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('catalog_skus')]
        
        # Add price_updated_at if missing
        if 'price_updated_at' not in columns:
            op.add_column('catalog_skus', sa.Column('price_updated_at', sa.DateTime(), nullable=True))
            
        # Add source_id if missing
        if 'source_id' not in columns:
            op.add_column('catalog_skus', sa.Column('source_id', sa.String(100), nullable=True))

        # Add last_synced_at if missing
        if 'last_synced_at' not in columns:
            op.add_column('catalog_skus', sa.Column('last_synced_at', sa.DateTime(), nullable=True))

        # Ensure created_at exists (it should, but safety first for drift repair)
        if 'created_at' not in columns:
             op.add_column('catalog_skus', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

        # Ensure updated_at exists
        if 'updated_at' not in columns:
             op.add_column('catalog_skus', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    # We do not drop these columns in downgrade as they might contain valuable data
    # and this is a repair migration.
    pass
