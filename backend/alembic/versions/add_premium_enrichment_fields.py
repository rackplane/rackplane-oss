# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
"""
Add premium enrichment fields to catalog_skus

Revision ID: add_premium_enrichment_fields
Revises: add_asset_type_features
Create Date: 2025-12-30

Premium fields: lead_time_days, in_stock, spec_sheet_url, warranty_months
"""
from alembic import op
import sqlalchemy as sa
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from alembic_helpers import column_exists


# revision identifiers, used by Alembic.
revision = 'add_premium_enrichment_fields'
down_revision = 'add_asset_type_features'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    
    # Add premium enrichment columns (idempotent)
    if not column_exists(conn, 'catalog_skus', 'lead_time_days'):
        op.add_column('catalog_skus', sa.Column(
            'lead_time_days', sa.Integer(), nullable=True,
            comment='Estimated lead time in days'
        ))
    
    if not column_exists(conn, 'catalog_skus', 'in_stock'):
        op.add_column('catalog_skus', sa.Column(
            'in_stock', sa.Boolean(), nullable=True,
            comment='Whether item is in stock'
        ))
    
    if not column_exists(conn, 'catalog_skus', 'spec_sheet_url'):
        op.add_column('catalog_skus', sa.Column(
            'spec_sheet_url', sa.String(500), nullable=True,
            comment='Premium detailed spec sheet PDF'
        ))
    
    if not column_exists(conn, 'catalog_skus', 'warranty_months'):
        op.add_column('catalog_skus', sa.Column(
            'warranty_months', sa.Integer(), nullable=True,
            comment='Warranty period in months'
        ))


def downgrade():
    conn = op.get_bind()
    
    if column_exists(conn, 'catalog_skus', 'warranty_months'):
        op.drop_column('catalog_skus', 'warranty_months')
    
    if column_exists(conn, 'catalog_skus', 'spec_sheet_url'):
        op.drop_column('catalog_skus', 'spec_sheet_url')
    
    if column_exists(conn, 'catalog_skus', 'in_stock'):
        op.drop_column('catalog_skus', 'in_stock')
    
    if column_exists(conn, 'catalog_skus', 'lead_time_days'):
        op.drop_column('catalog_skus', 'lead_time_days')
