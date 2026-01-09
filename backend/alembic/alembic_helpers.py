"""
Alembic Migration Helpers

Reusable idempotency check functions for migrations.
Import these in your migration files to ensure safe operations.

Usage:
    from alembic_helpers import index_exists, constraint_exists, column_exists

Example:
    def upgrade():
        conn = op.get_bind()
        if not index_exists(conn, 'my_index'):
            op.create_index('my_index', 'my_table', ['column'])
"""

import sqlalchemy as sa


def index_exists(conn, index_name: str) -> bool:
    """Check if an index exists in pg_indexes."""
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint OR index with this name exists.
    
    IMPORTANT: PostgreSQL unique constraints create backing indexes
    with the same name. Must check BOTH pg_constraint AND pg_indexes
    to avoid 'relation already exists' errors.
    """
    # Check pg_constraint first
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name"
    ), {"name": constraint_name})
    if result.fetchone() is not None:
        return True
    
    # Also check pg_indexes (unique constraints create backing indexes)
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": constraint_name})
    return result.fetchone() is not None


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = :table AND column_name = :column
    """), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = :name AND table_schema = 'public'
    """), {"name": table_name})
    return result.fetchone() is not None


def enum_exists(conn, enum_name: str) -> bool:
    """Check if an enum type exists in pg_type."""
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = :name"
    ), {"name": enum_name})
    return result.fetchone() is not None


def fk_constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a foreign key constraint exists."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_constraint 
        WHERE conname = :name AND contype = 'f'
    """), {"name": constraint_name})
    return result.fetchone() is not None


def pk_constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a primary key constraint exists."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_constraint 
        WHERE conname = :name AND contype = 'p'
    """), {"name": constraint_name})
    return result.fetchone() is not None
