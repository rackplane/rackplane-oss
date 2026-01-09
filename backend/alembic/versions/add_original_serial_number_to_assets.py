"""add original_serial_number to assets

Revision ID: add_original_serial_number
Revises: 
Create Date: 2024-11-30 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_original_serial_number'
down_revision = 'add_container_stock_thresholds'  # Set to one of the latest migrations
branch_labels = None
depends_on = None


def upgrade():
    # Add original_serial_number column to track the initial/auto-generated serial number
    # This allows QR codes to still match assets even after the serial number is updated
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    if 'original_serial_number' not in columns:
        op.add_column('assets', sa.Column('original_serial_number', sa.String(200), nullable=True, comment='Original/initial serial number (for QR code matching after updates)'))
        
        # For existing assets, set original_serial_number to current serial_number
        # This ensures existing QR codes continue to work
        op.execute("""
            UPDATE assets 
            SET original_serial_number = serial_number 
            WHERE original_serial_number IS NULL
        """)


def downgrade():
    op.drop_column('assets', 'original_serial_number')

