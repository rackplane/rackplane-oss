"""add_installed_transceiver_id_to_network_ports

Revision ID: ffd4bd8c3932
Revises: 3f82a1b3c9e7
Create Date: 2025-12-19 18:22:18.440839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffd4bd8c3932'
down_revision: Union[str, None] = '3f82a1b3c9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add installed_transceiver_id column to network_ports table (idempotent)
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('network_ports')]

    if 'installed_transceiver_id' not in columns:
        op.add_column('network_ports', sa.Column('installed_transceiver_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_network_ports_installed_transceiver',
            'network_ports', 'assets',
            ['installed_transceiver_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # Make downgrade idempotent
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if constraint exists before dropping
    constraints = [c['name'] for c in inspector.get_foreign_keys('network_ports')]
    if 'fk_network_ports_installed_transceiver' in constraints:
        op.drop_constraint('fk_network_ports_installed_transceiver', 'network_ports', type_='foreignkey')

    # Check if column exists before dropping
    columns = [col['name'] for col in inspector.get_columns('network_ports')]
    if 'installed_transceiver_id' in columns:
        op.drop_column('network_ports', 'installed_transceiver_id')

