"""Add source_id to catalog_skus manual

Revision ID: f6d783bd14ec
Revises: add_catalog_submissions
Create Date: 2026-01-01 03:37:44.272534

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = 'f6d783bd14ec'
down_revision: Union[str, None] = 'add_catalog_submissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Helpers copied for robustness/idempotency
def column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = :table AND column_name = :column
    """), {"table": table_name, "column": column_name})
    return result.fetchone() is not None

def index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None

def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add source_id to catalog_skus (Fix DuplicateColumn by checking existence)
    if not column_exists(conn, 'catalog_skus', 'source_id'):
        op.add_column('catalog_skus', sa.Column('source_id', sa.String(length=100), nullable=True, comment='ID in the upstream RackPlane API (if synced)'))
    
    if not index_exists(conn, 'ix_catalog_skus_source_id'):
        op.create_index(op.f('ix_catalog_skus_source_id'), 'catalog_skus', ['source_id'], unique=False)

    # 2. Add missing columns to api_customers (Fix UndefinedColumn in tests)
    if not column_exists(conn, 'api_customers', 'contribution_count'):
        op.add_column('api_customers', sa.Column('contribution_count', sa.Integer(), server_default='0', nullable=True))
    
    if not column_exists(conn, 'api_customers', 'contributor_since'):
        op.add_column('api_customers', sa.Column('contributor_since', sa.DateTime(), nullable=True))

    if not column_exists(conn, 'api_customers', 'is_lifetime_contributor'):
        # Note: Postgres boolean literals can be used
        op.add_column('api_customers', sa.Column('is_lifetime_contributor', sa.Boolean(), server_default='false', nullable=True))

    if not column_exists(conn, 'api_customers', 'customer_metadata'):
        op.add_column('api_customers', sa.Column('customer_metadata', sa.JSON(), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    
    if index_exists(conn, 'ix_catalog_skus_source_id'):
        op.drop_index(op.f('ix_catalog_skus_source_id'), table_name='catalog_skus')
        
    if column_exists(conn, 'catalog_skus', 'source_id'):
        op.drop_column('catalog_skus', 'source_id')
    
    # Drop api_customers columns
    for col in ['contribution_count', 'contributor_since', 'is_lifetime_contributor', 'customer_metadata']:
        if column_exists(conn, 'api_customers', col):
            op.drop_column('api_customers', col)
