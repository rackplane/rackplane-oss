"""add netbox sync tracking fields

Revision ID: add_netbox_sync_fields
Revises: fix_incorrect_storage_box_thresholds
Create Date: 2025-12-03

Adds sync tracking fields to assets table for bidirectional NetBox synchronization.
This is required for the premium "netbox_bidirectional_sync" feature.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_netbox_sync_fields'
down_revision = 'fix_incorrect_stock_thresholds'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add NetBox sync tracking fields to assets table.
    
    Adds:
    - last_synced_at: Timestamp of last successful sync with NetBox
    - last_modified_at: Timestamp of last modification (auto-updated)
    - sync_metadata: JSON field for sync state (conflicts, etags, etc.)
    
    These fields enable bidirectional sync between RackPlane and NetBox
    by tracking modification times and conflict state.
    """
    from sqlalchemy import inspect
    
    # Check if columns already exist (idempotency)
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    # Add last_synced_at - tracks last successful sync
    if 'last_synced_at' not in columns:
        op.add_column('assets', 
            sa.Column('last_synced_at', sa.DateTime(), 
                     nullable=True, 
                     comment='Last successful sync with NetBox (premium feature)')
        )
    
    # Add last_modified_at - auto-updated on record change
    if 'last_modified_at' not in columns:
        op.add_column('assets',
            sa.Column('last_modified_at', sa.DateTime(), 
                     nullable=True,
                     comment='Last modification timestamp (for sync conflict detection)')
        )
        
        # Set initial value to updated_at for existing records
        op.execute('UPDATE assets SET last_modified_at = updated_at WHERE last_modified_at IS NULL')
    
    # Add sync_metadata - stores sync state and conflict information
    if 'sync_metadata' not in columns:
        op.add_column('assets',
            sa.Column('sync_metadata', sa.JSON(), 
                     nullable=True,
                     server_default='{}',
                     comment='Sync metadata: conflict state, etags, last sync source, etc.')
        )


def downgrade() -> None:
    """Remove NetBox sync tracking fields"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    if 'sync_metadata' in columns:
        op.drop_column('assets', 'sync_metadata')
    
    if 'last_modified_at' in columns:
        op.drop_column('assets', 'last_modified_at')
    
    if 'last_synced_at' in columns:
        op.drop_column('assets', 'last_synced_at')
