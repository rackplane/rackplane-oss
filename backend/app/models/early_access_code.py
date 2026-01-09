# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Early Access Code Model

"""
Early Access Code Model
Stores early access codes for signup validation
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from datetime import datetime
from app.core.database import Base


class EarlyAccessCode(Base):
    """
    Early access code for signup validation.
    
    Codes are generated when users request early access on www.rackplane.com
    and sent via email. Users must provide a valid code to sign up.
    """
    __tablename__ = "early_access_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(200), nullable=False, index=True)  # Email that requested it
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiry
    used_at = Column(DateTime(timezone=True), nullable=True)  # When code was used
    used_by_email = Column(String(200), nullable=True)  # Email that used it for signup
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)  # Optional admin notes

