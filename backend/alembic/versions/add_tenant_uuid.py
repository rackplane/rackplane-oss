"""Add UUID to Tenant model

Revision ID: add_tenant_uuid
Revises: repair_catalog_drift
Create Date: 2026-01-02 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid
import sys
import os

# Import idempotency helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alembic_helpers import column_exists, constraint_exists, index_exists

# revision identifiers, used by Alembic.
revision = 'add_tenant_uuid'
down_revision = 'repair_catalog_drift'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Add uuid column as nullable first (only if it doesn't exist)
    if not column_exists(connection, 'tenants', 'uuid'):
        op.add_column('tenants', sa.Column('uuid', sa.String(36), nullable=True))

    # Backfill existing tenants with UUIDs (only if there are NULL values)
    null_count = connection.execute(sa.text("SELECT COUNT(*) FROM tenants WHERE uuid IS NULL")).scalar()
    if null_count > 0:
        # Try PostgreSQL's gen_random_uuid() for efficient bulk update
        # Falls back to row-by-row for databases without UUID support
        try:
            # PostgreSQL has gen_random_uuid() built-in (9.4+)
            connection.execute(sa.text(
                "UPDATE tenants SET uuid = gen_random_uuid()::text WHERE uuid IS NULL"
            ))
        except Exception:
            # Fallback for databases without native UUID generation (SQLite, older MySQL)
            tenants = connection.execute(sa.text("SELECT id FROM tenants WHERE uuid IS NULL"))
            for row in tenants:
                connection.execute(
                    sa.text("UPDATE tenants SET uuid = :uuid WHERE id = :id"),
                    {"uuid": str(uuid.uuid4()), "id": row.id}
                )

        # Verify all tenants have UUIDs after backfilling
        null_count_after = connection.execute(sa.text("SELECT COUNT(*) FROM tenants WHERE uuid IS NULL")).scalar()
        if null_count_after > 0:
            raise Exception(f"Migration failed: {null_count_after} tenants still have NULL uuid after backfill")

    # Make column non-nullable after backfilling to enforce data integrity
    # Only alter if column is still nullable
    result = connection.execute(sa.text("""
        SELECT is_nullable FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'uuid'
    """))
    row = result.fetchone()
    if row and row[0] == 'YES':
        op.alter_column('tenants', 'uuid', nullable=False)

    # Add unique constraint and index (only if they don't exist)
    if not constraint_exists(connection, 'uq_tenants_uuid'):
        op.create_unique_constraint('uq_tenants_uuid', 'tenants', ['uuid'])
    
    if not index_exists(connection, 'ix_tenants_uuid'):
        op.create_index('ix_tenants_uuid', 'tenants', ['uuid'])


def downgrade() -> None:
    connection = op.get_bind()
    
    # Drop index and constraint first (only if they exist)
    if index_exists(connection, 'ix_tenants_uuid'):
        op.drop_index('ix_tenants_uuid', 'tenants')
    
    if constraint_exists(connection, 'uq_tenants_uuid'):
        op.drop_constraint('uq_tenants_uuid', 'tenants', type_='unique')

    # Drop the column (only if it exists)
    if column_exists(connection, 'tenants', 'uuid'):
        op.drop_column('tenants', 'uuid')
