"""add_print_jobs_table

Revision ID: 9bdcb39ba354
Revises: e2e2ac4a234e
Create Date: 2025-12-01 21:34:26.775053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9bdcb39ba354'
down_revision: Union[str, None] = 'e2e2ac4a234e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types if they don't exist (idempotent)
    # Pattern matches add_user_role_column migration
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if printjobtype enum exists
    result = conn.execute(sa.text("SELECT typname FROM pg_type WHERE typname = 'printjobtype'"))
    if result.fetchone() is None:
        op.execute("CREATE TYPE printjobtype AS ENUM ('ASSET_LABEL', 'CONTAINER_LABEL', 'RACK_LABEL')")
    
    # Check if printjobstatus enum exists
    result = conn.execute(sa.text("SELECT typname FROM pg_type WHERE typname = 'printjobstatus'"))
    if result.fetchone() is None:
        op.execute("CREATE TYPE printjobstatus AS ENUM ('PENDING', 'ASSIGNED', 'PRINTING', 'COMPLETED', 'FAILED', 'CANCELLED')")
    
    # Create print_jobs table if it doesn't exist
    # Use postgresql.ENUM with create_type=False to prevent SQLAlchemy from trying to create the enum
    # The enum types are already created above
    if 'print_jobs' not in inspector.get_table_names():
        op.create_table(
        'print_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_type', postgresql.ENUM('ASSET_LABEL', 'CONTAINER_LABEL', 'RACK_LABEL', name='printjobtype', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'ASSIGNED', 'PRINTING', 'COMPLETED', 'FAILED', 'CANCELLED', name='printjobstatus', create_type=False), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('container_id', sa.Integer(), nullable=True),
        sa.Column('rack_id', sa.Integer(), nullable=True),
        sa.Column('label_size', sa.String(length=20), nullable=False),
        sa.Column('printer_ip', sa.String(length=50), nullable=True),
        sa.Column('instance', sa.Integer(), nullable=True),
        sa.Column('total_instances', sa.Integer(), nullable=True),
        sa.Column('label_data', sa.JSON(), nullable=True),
        sa.Column('label_image_url', sa.String(length=500), nullable=True),
        sa.Column('assigned_agent_id', sa.String(length=100), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('printer_response', sa.JSON(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('custom_fields', sa.JSON(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['container_id'], ['storage_containers.id'], ),
        sa.ForeignKeyConstraint(['rack_id'], ['racks.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        # Create indexes only if table was just created
        op.create_index(op.f('ix_print_jobs_id'), 'print_jobs', ['id'], unique=False)
        op.create_index(op.f('ix_print_jobs_status'), 'print_jobs', ['status'], unique=False)
        op.create_index(op.f('ix_print_jobs_assigned_agent_id'), 'print_jobs', ['assigned_agent_id'], unique=False)
        op.create_index(op.f('ix_print_jobs_created_at'), 'print_jobs', ['created_at'], unique=False)
    
    # Create print_agents table if it doesn't exist
    if 'print_agents' not in inspector.get_table_names():
        op.create_table(
        'print_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('agent_name', sa.String(length=200), nullable=True),
        sa.Column('agent_version', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('heartbeat_interval_seconds', sa.Integer(), nullable=True),
        sa.Column('supported_label_sizes', sa.JSON(), nullable=True),
        sa.Column('printer_ips', sa.JSON(), nullable=True),
        sa.Column('max_concurrent_jobs', sa.Integer(), nullable=True),
        sa.Column('total_jobs_completed', sa.Integer(), nullable=True),
        sa.Column('total_jobs_failed', sa.Integer(), nullable=True),
        sa.Column('last_job_at', sa.DateTime(), nullable=True),
        sa.Column('hostname', sa.String(length=200), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('operating_system', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('custom_fields', sa.JSON(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id')
        )
        # Create indexes only if table was just created
        op.create_index(op.f('ix_print_agents_id'), 'print_agents', ['id'], unique=False)
        op.create_index(op.f('ix_print_agents_agent_id'), 'print_agents', ['agent_id'], unique=True)
        op.create_index(op.f('ix_print_agents_last_heartbeat'), 'print_agents', ['last_heartbeat'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_print_agents_last_heartbeat'), table_name='print_agents')
    op.drop_index(op.f('ix_print_agents_agent_id'), table_name='print_agents')
    op.drop_index(op.f('ix_print_agents_id'), table_name='print_agents')
    op.drop_table('print_agents')
    op.drop_index(op.f('ix_print_jobs_created_at'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_assigned_agent_id'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_status'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_id'), table_name='print_jobs')
    op.drop_table('print_jobs')
    # Drop enums
    sa.Enum(name='printjobstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='printjobtype').drop(op.get_bind(), checkfirst=True)

