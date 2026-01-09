"""add_token_id_to_audit_logs

Revision ID: add_token_id_to_audit_logs
Revises: add_api_keys_table
Create Date: 2025-12-01 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_token_id_to_audit_logs'
down_revision: Union[str, None] = 'add_api_keys_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    
    if 'api_key_id' in columns:
        # Column already exists, skip
        return
    
    # Add api_key_id column to audit_logs
    op.add_column(
        'audit_logs',
        sa.Column('api_key_id', sa.Integer(), nullable=True, comment='ID of API key used (if authenticated via API key)')
    )
    
    # Create index for performance
    op.create_index(op.f('ix_audit_logs_api_key_id'), 'audit_logs', ['api_key_id'], unique=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_audit_logs_api_key_id',
        'audit_logs',
        'api_keys',
        ['api_key_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_audit_logs_api_key_id', 'audit_logs', type_='foreignkey')
    
    # Drop index
    op.drop_index(op.f('ix_audit_logs_api_key_id'), table_name='audit_logs')
    
    # Drop column
    op.drop_column('audit_logs', 'api_key_id')

