"""add_unique_constraint_to_audit_logs

Revision ID: e2e2ac4a234e
Revises: 1864ebe8a518
Create Date: 2025-12-01 21:27:36.507549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2e2ac4a234e'
down_revision: Union[str, None] = '1864ebe8a518'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add unique constraint to prevent duplicate audit log entries.
    
    This constraint prevents the same audit log entry from being created multiple times
    with identical action, user, table, record, and timestamp. This addresses the issue
    where 245,755 duplicate entries were created due to a bug.
    
    Constraint: (action, user_id, username, table_name, record_id, created_at) must be unique
    """
    import sqlalchemy as sa
    from sqlalchemy import inspect
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    if 'audit_logs' in inspector.get_table_names():
        # Check if constraint already exists
        result = connection.execute(sa.text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'audit_logs' AND indexname = 'idx_audit_logs_unique_action'
        """))
        exists = result.scalar() > 0
        
        if not exists:
            # First, remove duplicates (keep the first entry with lowest ID)
            # This must be done before adding the unique constraint
            connection.execute(sa.text("""
                DELETE FROM audit_logs
                WHERE id IN (
                    SELECT id
                    FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY action, user_id, username, table_name, record_id, created_at
                                   ORDER BY id
                               ) as rn
                        FROM audit_logs
                    ) as ranked
                    WHERE rn > 1
                )
            """))
            connection.commit()
            
            # Create unique index to prevent future duplicates
            # Use raw SQL to ensure it works correctly
            connection.execute(sa.text("""
                CREATE UNIQUE INDEX idx_audit_logs_unique_action 
                ON audit_logs (action, user_id, username, table_name, record_id, created_at)
            """))
            connection.commit()


def downgrade() -> None:
    """
    Remove the unique constraint.
    
    WARNING: This will allow duplicate audit log entries again.
    Only use this if you have a specific reason.
    """
    import sqlalchemy as sa
    connection = op.get_bind()
    
    # Check if index exists before dropping
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM pg_indexes 
        WHERE tablename = 'audit_logs' AND indexname = 'idx_audit_logs_unique_action'
    """))
    exists = result.scalar() > 0
    
    if exists:
        op.drop_index('idx_audit_logs_unique_action', table_name='audit_logs')

