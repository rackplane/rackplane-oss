"""create central_catalog_submissions table

Revision ID: fb931faace47
Revises: 6bb877509f11
Create Date: 2026-01-01 21:06:23.020305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb931faace47'
down_revision: Union[str, None] = '6bb877509f11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError
from sqlalchemy import inspect

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Safely create Enum type
    submission_status = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='submissionstatus')
    try:
        submission_status.create(bind, checkfirst=True)
    except ProgrammingError:
        pass

    if 'central_catalog_submissions' not in inspector.get_table_names():
        op.create_table('central_catalog_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        # Use postgresql.ENUM explicitly with create_type=False
        sa.Column('status', postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='submissionstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('proposed_data', sa.JSON(), nullable=False, comment='Complete SKU data payload'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True, comment='Reason for rejection or internal notes'),
        sa.ForeignKeyConstraint(['customer_id'], ['api_customers.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_central_catalog_submissions_customer_id'), 'central_catalog_submissions', ['customer_id'], unique=False)
        op.create_index(op.f('ix_central_catalog_submissions_id'), 'central_catalog_submissions', ['id'], unique=False)
        op.create_index(op.f('ix_central_catalog_submissions_status'), 'central_catalog_submissions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_central_catalog_submissions_status'), table_name='central_catalog_submissions')
    op.drop_index(op.f('ix_central_catalog_submissions_id'), table_name='central_catalog_submissions')
    op.drop_index(op.f('ix_central_catalog_submissions_customer_id'), table_name='central_catalog_submissions')
    op.drop_table('central_catalog_submissions')
    # Drop enum type
    postgresql.ENUM(name='submissionstatus').drop(op.get_bind(), checkfirst=True)

