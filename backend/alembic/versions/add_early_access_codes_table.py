"""add_early_access_codes_table

Revision ID: add_early_access_codes_table
Revises: repair_catalog_schema_drift
Create Date: 2025-12-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_early_access_codes_table'
down_revision: Union[str, None] = 'repair_catalog_drift'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if early_access_codes table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'early_access_codes' in tables:
        # Table already exists, skip creation
        return
    
    # Create early_access_codes table
    op.create_table(
        'early_access_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_email', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index(op.f('ix_early_access_codes_id'), 'early_access_codes', ['id'], unique=False)
    op.create_index(op.f('ix_early_access_codes_code'), 'early_access_codes', ['code'], unique=True)
    op.create_index(op.f('ix_early_access_codes_email'), 'early_access_codes', ['email'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_early_access_codes_email'), table_name='early_access_codes')
    op.drop_index(op.f('ix_early_access_codes_code'), table_name='early_access_codes')
    op.drop_index(op.f('ix_early_access_codes_id'), table_name='early_access_codes')
    
    # Drop table
    op.drop_table('early_access_codes')

