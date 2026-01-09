"""add_email_notification_preferences

Revision ID: add_email_notification_preferences
Revises: add_audit_logs_table
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_email_notif_prefs'  # Shortened to fit alembic_version table (32 char limit)
down_revision: Union[str, None] = 'add_audit_logs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add email column if it doesn't exist
    if 'email' not in columns:
        op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True, comment='Email address for notifications'))
        # Create index on email column
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    
    # Add notification_preferences column if it doesn't exist
    if 'notification_preferences' not in columns:
        # Default notification preferences
        default_prefs = {
            "email_enabled": True,
            "low_stock": True,
            "maintenance": True,
            "warranty": True
        }
        op.add_column(
            'users',
            sa.Column(
                'notification_preferences',
                postgresql.JSON(astext_type=sa.Text()),
                nullable=True,
                comment='Email notification preferences'
            )
        )


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    
    # Drop index if it exists
    if 'ix_users_email' in indexes:
        op.drop_index(op.f('ix_users_email'), table_name='users')
    
    # Drop columns if they exist
    if 'notification_preferences' in columns:
        op.drop_column('users', 'notification_preferences')
    
    if 'email' in columns:
        op.drop_column('users', 'email')

