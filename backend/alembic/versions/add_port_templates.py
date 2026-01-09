"""add_port_templates_table

Revision ID: add_port_templates
Revises: repair_catalog_drift
Create Date: 2025-12-17

Add port_templates table for storing network device port configuration templates.
Part of Phase 1: Port-to-Port Connections feature.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_port_templates'
down_revision = 'add_early_access_codes_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create port_templates table if it doesn't exist"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table already exists (idempotency)
    if 'port_templates' not in inspector.get_table_names():
        op.create_table(
            'port_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('manufacturer', sa.String(100), nullable=False),
            sa.Column('model', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('port_definitions', postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_port_templates_tenant_id'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tenant_id', 'manufacturer', 'model', name='uq_port_template_mfg_model')
        )
        op.create_index('idx_port_templates_tenant', 'port_templates', ['tenant_id'])
        op.create_index('idx_port_templates_manufacturer', 'port_templates', ['manufacturer'])
        op.create_index('idx_port_templates_model', 'port_templates', ['model'])


def downgrade() -> None:
    """Drop port_templates table"""
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'port_templates' in inspector.get_table_names():
        op.drop_index('idx_port_templates_model', table_name='port_templates')
        op.drop_index('idx_port_templates_manufacturer', table_name='port_templates')
        op.drop_index('idx_port_templates_tenant', table_name='port_templates')
        op.drop_table('port_templates')
