# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Environment Model
DEV Troubleshooting environment management

This model represents development/testing environments that can be managed
through the DEV Troubleshooting interface. Each environment has SSH and IPMI
access information for remote management.

SECURITY NOTE - Internal Use Only:
    Passwords (ssh_password, ipmi_password) are stored in PLAIN TEXT for
    internal debugging and operational convenience. These are intended for:
    - Internal development/testing environments
    - Quick access during server crashes/outages
    - Engineer troubleshooting workflows
    
    These passwords are NOT encrypted and should NEVER be used for:
    - Production systems accessible from the internet
    - Customer-facing environments
    - Any system with sensitive data
    
    This is an intentional design decision for operational efficiency in
    internal environments only.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class Environment(Base, TenantMixin):
    """
    Environment model for DEV troubleshooting.
    
    Represents a development/testing environment with SSH and IPMI access
    information. Used for remote server management and troubleshooting.
    
    Attributes:
        id: Primary key
        name: Display name (e.g., "Production", "Staging", "Development")
        ssh_link: SSH connection string (e.g., "server.example.com")
        ipmi_link: IPMI web interface URL
        ssh_username: SSH username (optional)
        ssh_password: SSH password (optional)
        ipmi_username: IPMI username (optional)
        ipmi_password: IPMI password (optional)
        tenant_id: Foreign key to tenants table (from TenantMixin)
        created_at: Timestamp when environment was created
        updated_at: Timestamp when environment was last updated
    """
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="Environment name")
    ssh_link = Column(String(200), nullable=False, comment="SSH connection string")
    ipmi_link = Column(String(200), nullable=False, comment="IPMI web interface URL")
    ssh_username = Column(String(100), nullable=True, comment="SSH username")
    ssh_password = Column(String(200), nullable=True, comment="SSH password (plain text, internal use only - see model docstring)")
    ipmi_username = Column(String(100), nullable=True, comment="IPMI username")
    ipmi_password = Column(String(200), nullable=True, comment="IPMI password (plain text, internal use only - see model docstring)")
    # tenant_id is inherited from TenantMixin
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Environment(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"

