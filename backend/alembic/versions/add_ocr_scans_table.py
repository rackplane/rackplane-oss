"""add_ocr_scans_table

Revision ID: add_ocr_scans
Revises: e4316bf57e1e
Create Date: 2025-12-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_ocr_scans'
down_revision: Union[str, Sequence[str], None] = 'add_cached_skus'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists (handles re-runs)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ocr_scans')"
    ))
    table_exists = result.scalar()
    
    if table_exists:
        # Table already exists, skip creation
        return
    
    # Create ocr_scans table
    op.create_table(
        'ocr_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        # Image Fingerprinting
        sa.Column('image_hash', sa.String(length=64), nullable=True, comment='SHA256 hash for exact match'),
        sa.Column('image_phash', sa.String(length=16), nullable=True, comment='Perceptual hash for similar images'),
        sa.Column('image_url', sa.String(length=500), nullable=True, comment='MinIO/S3 URL to stored image'),
        
        # Tesseract Results
        sa.Column('tesseract_text', sa.Text(), nullable=True, comment='Raw Tesseract OCR output'),
        sa.Column('tesseract_confidence', sa.String(length=20), nullable=True, comment='Confidence level: low/medium/high'),
        sa.Column('tesseract_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='PSM mode, preprocessing flags, timing'),
        
        # Cloud OCR Results
        sa.Column('cloud_text', sa.Text(), nullable=True, comment='Cloud OCR output'),
        sa.Column('cloud_confidence', sa.String(length=20), nullable=True, comment='Cloud confidence: low/medium/high'),
        sa.Column('cloud_service', sa.String(length=50), nullable=True, comment='Service used: google_vision, aws_textract'),
        sa.Column('cloud_scanned_at', sa.DateTime(), nullable=True, comment='When cloud OCR was performed'),
        sa.Column('cloud_cost_credits', sa.Integer(), nullable=True, comment='Credits consumed for cloud OCR'),
        
        # Parsed Data
        sa.Column('parsed_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Structured data extracted from OCR'),
        
        # Matching Results
        sa.Column('matched_sku_id', sa.Integer(), nullable=True),
        sa.Column('matched_asset_id', sa.Integer(), nullable=True),
        sa.Column('match_type', sa.String(length=20), nullable=True, comment='Match type: exact_hash, similar_hash, sku_lookup'),
        sa.Column('match_confidence', sa.Float(), nullable=True, comment='Match confidence 0.0-1.0'),
        
        # User Corrections
        sa.Column('user_corrected', sa.Boolean(), nullable=True, server_default='false', comment='Whether user made corrections'),
        sa.Column('corrected_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='User-provided corrections'),
        
        # Scan Status and Lifecycle
        sa.Column('scan_status', sa.String(length=20), nullable=True, server_default='pending', comment='Status: pending/processing/success/failed'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if scan failed'),
        
        # Retention Policy
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='NULL = never expires'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # Constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['matched_sku_id'], ['vendor_skus.id'], ),
        sa.ForeignKeyConstraint(['matched_asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_ocr_scans_id'), 'ocr_scans', ['id'], unique=False)
    op.create_index(op.f('ix_ocr_scans_tenant_id'), 'ocr_scans', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_ocr_scans_user_id'), 'ocr_scans', ['user_id'], unique=False)
    op.create_index(op.f('ix_ocr_scans_image_hash'), 'ocr_scans', ['image_hash'], unique=False)
    op.create_index(op.f('ix_ocr_scans_image_phash'), 'ocr_scans', ['image_phash'], unique=False)
    op.create_index(op.f('ix_ocr_scans_matched_sku_id'), 'ocr_scans', ['matched_sku_id'], unique=False)
    op.create_index(op.f('ix_ocr_scans_matched_asset_id'), 'ocr_scans', ['matched_asset_id'], unique=False)
    op.create_index(op.f('ix_ocr_scans_user_corrected'), 'ocr_scans', ['user_corrected'], unique=False)
    op.create_index(op.f('ix_ocr_scans_scan_status'), 'ocr_scans', ['scan_status'], unique=False)
    op.create_index(op.f('ix_ocr_scans_expires_at'), 'ocr_scans', ['expires_at'], unique=False)
    
    # Composite indexes for common queries
    op.create_index('ix_ocr_scans_tenant_status', 'ocr_scans', ['tenant_id', 'scan_status'], unique=False)
    op.create_index('ix_ocr_scans_tenant_created', 'ocr_scans', ['tenant_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_ocr_scans_tenant_created', table_name='ocr_scans')
    op.drop_index('ix_ocr_scans_tenant_status', table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_expires_at'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_scan_status'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_user_corrected'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_matched_asset_id'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_matched_sku_id'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_image_phash'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_image_hash'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_user_id'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_tenant_id'), table_name='ocr_scans')
    op.drop_index(op.f('ix_ocr_scans_id'), table_name='ocr_scans')
    
    # Drop table
    op.drop_table('ocr_scans')
