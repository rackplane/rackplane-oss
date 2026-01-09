"""restore_racks_code_unique_constraint

Revision ID: 0e3a451519ca
Revises: cff3b4de952b
Create Date: 2025-11-30 19:14:34.871699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e3a451519ca'
down_revision: Union[str, Sequence[str], None] = 'cff3b4de952b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Restore unique constraint on racks.code per tenant.
    
    This constraint was accidentally dropped in migration cff3b4de952b.
    The constraint ensures that rack codes are unique within each tenant.
    """
    from sqlalchemy import inspect as sa_inspect
    
    connection = op.get_bind()
    inspector = sa_inspect(connection)
    
    # Check if the unique index already exists
    indexes = inspector.get_indexes('racks')
    index_exists = any(
        idx['name'] == 'idx_racks_code_tenant' and idx.get('unique', False)
        for idx in indexes
    )
    
    if not index_exists:
        # Check if there are any duplicate rack codes per tenant
        # If so, we can't create the constraint until duplicates are cleaned up
        result = connection.execute(sa.text("""
            SELECT code, tenant_id, COUNT(*) as cnt
            FROM racks
            GROUP BY code, tenant_id
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        if duplicates:
            raise Exception(
                f"Cannot create unique constraint: found {len(duplicates)} duplicate rack code(s) per tenant. "
                f"Please run cleanup_duplicate_racks.py --apply first."
            )
        
        # Create the unique index
        op.create_index(
            'idx_racks_code_tenant',
            'racks',
            ['code', 'tenant_id'],
            unique=True
        )
        print("✓ Created unique index idx_racks_code_tenant on racks(code, tenant_id)")
    else:
        print("✓ Unique index idx_racks_code_tenant already exists")


def downgrade() -> None:
    """
    Drop the unique constraint on racks.code per tenant.
    This reverses the upgrade and allows duplicate rack codes again.
    """
    from sqlalchemy import inspect as sa_inspect
    
    connection = op.get_bind()
    inspector = sa_inspect(connection)
    
    # Check if the index exists
    indexes = inspector.get_indexes('racks')
    index_exists = any(idx['name'] == 'idx_racks_code_tenant' for idx in indexes)
    
    if index_exists:
        op.drop_index('idx_racks_code_tenant', table_name='racks')
        print("✓ Dropped unique index idx_racks_code_tenant")
    else:
        print("✓ Unique index idx_racks_code_tenant does not exist")
