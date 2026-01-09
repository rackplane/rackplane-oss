"""Add catalog_submissions table

Revision ID: add_catalog_submissions
Revises: add_premium_enrichment_fields
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_catalog_submissions'
down_revision = 'add_premium_enrichment_fields'
branch_labels = None
depends_on = None


def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
    ), {"table_name": table_name})
    return result.scalar()


def index_exists(conn, index_name):
    """Check if an index exists in the database."""
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :index_name)"
    ), {"index_name": index_name})
    return result.scalar()


def upgrade():
    conn = op.get_bind()
    
    # Create catalog_submissions table if it doesn't exist
    if not table_exists(conn, 'catalog_submissions'):
        op.create_table(
            'catalog_submissions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('vendor', sa.String(100), nullable=False),
            sa.Column('sku', sa.String(100), nullable=False),
            sa.Column('data_snapshot', sa.JSON(), nullable=False),
            sa.Column('source_url', sa.String(500), nullable=True),
            sa.Column('submission_method', sa.String(50), nullable=False, server_default='manual_edit'),
            sa.Column('existing_catalog_sku_id', sa.Integer(), nullable=True),
            sa.Column('submitted_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('reviewed_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    
    # Create indexes if they don't exist
    if not index_exists(conn, 'ix_catalog_submissions_vendor'):
        op.create_index('ix_catalog_submissions_vendor', 'catalog_submissions', ['vendor'])
    
    if not index_exists(conn, 'ix_catalog_submissions_sku'):
        op.create_index('ix_catalog_submissions_sku', 'catalog_submissions', ['sku'])
    
    if not index_exists(conn, 'ix_catalog_submissions_status'):
        op.create_index('ix_catalog_submissions_status', 'catalog_submissions', ['status'])
    
    if not index_exists(conn, 'ix_catalog_submissions_submitted_by'):
        op.create_index('ix_catalog_submissions_submitted_by', 'catalog_submissions', ['submitted_by_user_id'])


def downgrade():
    conn = op.get_bind()
    
    if table_exists(conn, 'catalog_submissions'):
        op.drop_table('catalog_submissions')
