"""merge all migration heads - FINAL version

Revision ID: merge_all_migration_heads
Revises: add_sfp56_qsfp56
Create Date: 2025-12-19

After proper analysis, we found that add_sfp56_qsfp56 is the ONLY actual head.
All other migrations previously listed are ancestors of this chain or are
referenced by other migrations (they aren't heads).

The full chain is:
repair_catalog_drift -> add_early_access_codes_table -> add_port_templates
-> add_service_contracts -> migrate_connections_to_ports -> add_osfp_port_types
-> add_ui_preferences -> add_lane_encoding -> add_cable_end_types -> add_sfp56_qsfp56
"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence


# revision identifiers, used by Alembic.
revision = 'merge_all_migration_heads'
down_revision: Union[str, Sequence[str]] = 'add_sfp56_qsfp56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op merge migration - just marks end of chain."""
    pass


def downgrade() -> None:
    """No-op - nothing to downgrade."""
    pass
