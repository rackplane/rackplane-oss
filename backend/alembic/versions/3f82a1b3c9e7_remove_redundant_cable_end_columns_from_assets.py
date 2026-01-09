"""remove redundant cable end columns from assets

Revision ID: 3f82a1b3c9e7
Revises: c1072a3b5b96
Create Date: 2025-12-19 01:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '3f82a1b3c9e7'
down_revision = 'c1072a3b5b96'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    if 'connector_type_end_a' in columns:
        op.drop_column('assets', 'connector_type_end_a')
    if 'connector_type_end_b' in columns:
        op.drop_column('assets', 'connector_type_end_b')

def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    if 'connector_type_end_a' not in columns:
        op.add_column('assets', sa.Column('connector_type_end_a', sa.String(length=50), nullable=True))
    if 'connector_type_end_b' not in columns:
        op.add_column('assets', sa.Column('connector_type_end_b', sa.String(length=50), nullable=True))
