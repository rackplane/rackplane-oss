"""add_service_contracts

Revision ID: add_service_contracts
Revises: add_port_templates
Create Date: 2025-12-17

Add service_contracts and contract_asset_link tables.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_service_contracts'
down_revision = 'add_port_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    # Enum types
    # Check if enums exist before creating (Postgres)
    # Using 'execute' for raw SQL checks if needed, but SQLAlchemy usually handles CreateType with checkfirst=True if using TypeDecorator, 
    # but here we use native Enum which might error if exists.
    # However, alembic usually needs explicit type creation for Postgres Enums if they are not inline.
    # In the model, we use SQLEnum(EnumClass), so they are created inline or as types.
    # We'll rely on create_table to handle usages. ensuring unique types if possible.
    # But usually better to define them.
    
    # Create service_contracts table
    if 'service_contracts' not in tables:
        op.create_table(
            'service_contracts',
            sa.Column('id', sa.Integer(), nullable=False),
            # TenantMixin fields
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            
            # Basic info
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('contract_type', sa.Enum('support', 'warranty', 'extended_warranty', 'professional_services', 'maintenance', 'licensing', 'other', name='contracttype'), nullable=False),
            sa.Column('vendor', sa.String(length=255), nullable=False),
            
            # Dates
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('renewal_date', sa.Date(), nullable=True),
            
            # Financials
            sa.Column('total_cost', sa.Float(), nullable=True),
            sa.Column('cost_period', sa.Enum('one_time', 'monthly', 'quarterly', 'annual', 'multi_year', name='costperiod'), nullable=True),
            sa.Column('currency', sa.String(length=3), nullable=True),
            
            # Linkage
            sa.Column('po_number', sa.String(length=255), nullable=True),
            
            # Details
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('support_level', sa.String(length=100), nullable=True),
            sa.Column('per_unit_type', sa.Enum('flat_rate', 'per_node', 'per_rack', 'per_gpu', 'per_device', 'per_site', name='perunittype'), nullable=True),
            sa.Column('unit_count', sa.Integer(), nullable=True),
            
            # Status
            sa.Column('status', sa.Enum('pending', 'active', 'expiring_soon', 'expired', 'renewed', 'cancelled', name='contractstatus'), nullable=False),
            
            # Metadata
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_service_contracts_tenant_id'),
        )
        # Indexes
        op.create_index(op.f('ix_service_contracts_end_date'), 'service_contracts', ['end_date'], unique=False)
        op.create_index(op.f('ix_service_contracts_id'), 'service_contracts', ['id'], unique=False)
        op.create_index(op.f('ix_service_contracts_name'), 'service_contracts', ['name'], unique=False)
        op.create_index(op.f('ix_service_contracts_po_number'), 'service_contracts', ['po_number'], unique=False)
        op.create_index(op.f('ix_service_contracts_status'), 'service_contracts', ['status'], unique=False)
        op.create_index(op.f('ix_service_contracts_vendor'), 'service_contracts', ['vendor'], unique=False)

    # Create M2M table
    if 'contract_asset_link' not in tables:
        op.create_table(
            'contract_asset_link',
            sa.Column('contract_id', sa.Integer(), nullable=False),
            sa.Column('asset_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['contract_id'], ['service_contracts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('contract_id', 'asset_id')
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if 'contract_asset_link' in tables:
        op.drop_table('contract_asset_link')

    if 'service_contracts' in tables:
        op.drop_index(op.f('ix_service_contracts_vendor'), table_name='service_contracts')
        op.drop_index(op.f('ix_service_contracts_status'), table_name='service_contracts')
        op.drop_index(op.f('ix_service_contracts_po_number'), table_name='service_contracts')
        op.drop_index(op.f('ix_service_contracts_name'), table_name='service_contracts')
        op.drop_index(op.f('ix_service_contracts_id'), table_name='service_contracts')
        op.drop_index(op.f('ix_service_contracts_end_date'), table_name='service_contracts')
        op.drop_table('service_contracts')
    
    # Drop enums? Usually tricky in downgrade as other tables might use them? 
    # But here they are likely specific to this table.
    # We'll skip explicit Enum drop for now to avoid side effects if types were reused.
