# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Port Template Model"""

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class PortTemplate(Base, TenantMixin):
    """
    Port configuration templates for network devices.

    Defines the standard port layout for specific device models.
    Used to quickly provision ports when adding new devices.
    """
    __tablename__ = "port_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Device Identification
    manufacturer = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Port Configuration
    port_definitions = Column(JSONB, nullable=False, default=[])
    """
    JSON array of port configurations:
    [
        {
            "port_number": "1",
            "port_type": "rj45",
            "speed_mbps": 1000,
            "duplex": "full",
            "poe_capable": true,
            "poe_max_watts": 30
        },
        ...
    ]
    """

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'manufacturer', 'model', name='uq_port_template_mfg_model'),
    )

    def __repr__(self):
        port_count = len(self.port_definitions) if self.port_definitions else 0
        return f"<PortTemplate {self.manufacturer} {self.model} ({port_count} ports)>"
