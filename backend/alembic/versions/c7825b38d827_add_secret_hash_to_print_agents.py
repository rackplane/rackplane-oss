"""add_secret_hash_to_print_agents

Revision ID: c7825b38d827
Revises: 0b8dcffbf433
Create Date: 2025-12-02 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7825b38d827'
down_revision: Union[str, None] = '0b8dcffbf433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add secret_hash column to print_agents table for agent authentication.
    
    This migration adds the secret_hash column to enable secure agent authentication.
    Existing agents will have NULL secret_hash and will need to set a secret on first login.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    
    if 'print_agents' in table_names:
        columns = [col['name'] for col in inspector.get_columns('print_agents')]
        
        if 'secret_hash' not in columns:
            # Use op.execute for more reliable execution
            op.execute(sa.text("ALTER TABLE print_agents ADD COLUMN secret_hash VARCHAR(255)"))
            # Add comment
            op.execute(sa.text("COMMENT ON COLUMN print_agents.secret_hash IS 'Bcrypt hash of agent secret for authentication'"))


def downgrade() -> None:
    """
    Remove secret_hash column from print_agents table.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    
    if 'print_agents' in table_names:
        columns = [col['name'] for col in inspector.get_columns('print_agents')]
        
        if 'secret_hash' in columns:
            op.drop_column('print_agents', 'secret_hash')
