"""add_shopping_cart_tables

Revision ID: ba21f362d341
Revises: 96f8169a6abc
Create Date: 2025-12-23 22:02:25.041668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'ba21f362d341'
down_revision: Union[str, None] = '96f8169a6abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'shopping_carts' not in tables:
        op.create_table(
            'shopping_carts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False, server_default="My Cart"),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_shopping_carts_tenant_id'), 'shopping_carts', ['tenant_id'], unique=False)

    if 'cart_items' not in tables:
        op.create_table(
            'cart_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cart_id', sa.Integer(), nullable=False),
            sa.Column('catalog_sku_id', sa.Integer(), nullable=True),
            sa.Column('vendor_sku_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default="1"),
            sa.Column('unit_price', sa.Float(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['cart_id'], ['shopping_carts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['catalog_sku_id'], ['catalog_skus.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['vendor_sku_id'], ['vendor_skus.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            # Ensure at least one SKU reference
            sa.CheckConstraint(
                'catalog_sku_id IS NOT NULL OR vendor_sku_id IS NOT NULL',
                name='ck_cart_items_at_least_one_sku'
            ),
            # Ensure quantity is valid
            sa.CheckConstraint(
                'quantity >= 1 AND quantity <= 10000',  # MAX_ITEM_QUANTITY from model
                name='ck_cart_items_quantity_range'
            ),
        )
        op.create_index(op.f('ix_cart_items_tenant_id'), 'cart_items', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_cart_items_cart_id'), 'cart_items', ['cart_id'], unique=False)
        # Composite index for efficient SKU lookups, matching model definition
        op.create_index('ix_cart_items_cart_sku', 'cart_items', ['cart_id', 'vendor_sku_id', 'catalog_sku_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'cart_items' in tables:
        op.drop_table('cart_items')
    if 'shopping_carts' in tables:
        op.drop_table('shopping_carts')
