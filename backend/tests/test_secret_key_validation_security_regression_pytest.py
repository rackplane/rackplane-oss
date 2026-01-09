# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression Test: SECRET_KEY Validation Security
Tests that SECRET_KEY validation prevents default value in production
"""

import pytest
import os
from pydantic import ValidationError


@pytest.mark.integration
@pytest.mark.regression
def test_secret_key_rejects_default_in_production():
    """
    REGRESSION: SECRET_KEY must not be default value in production
    
    Bug: SECRET_KEY defaulted to "your-secret-key-change-in-production",
    allowing attackers to forge JWT tokens if deployed without override.
    
    Fix: Settings validation raises ValueError if default key is used when DEBUG=False.
    
    This test verifies:
    1. Default SECRET_KEY with DEBUG=False raises ValueError
    2. Default SECRET_KEY with DEBUG=True logs warning but allows (development)
    3. Custom SECRET_KEY works in both modes
    """
    # Test 1: Default key in production (DEBUG=False) should raise error
    with pytest.raises(ValidationError) as exc_info:
        from app.core.config import Settings
        # Temporarily override environment to force default
        original_debug = os.environ.get('DEBUG')
        original_secret = os.environ.get('SECRET_KEY')
        try:
            if 'DEBUG' in os.environ:
                del os.environ['DEBUG']
            if 'SECRET_KEY' in os.environ:
                del os.environ['SECRET_KEY']
            
            # Create settings with default key and DEBUG=False
            settings = Settings(
                SECRET_KEY="your-secret-key-change-in-production",
                DEBUG=False
            )
        finally:
            # Restore environment
            if original_debug:
                os.environ['DEBUG'] = original_debug
            elif 'DEBUG' in os.environ:
                del os.environ['DEBUG']
            if original_secret:
                os.environ['SECRET_KEY'] = original_secret
            elif 'SECRET_KEY' in os.environ:
                del os.environ['SECRET_KEY']
    
    # Verify error message mentions SECRET_KEY
    error_str = str(exc_info.value)
    assert "SECRET_KEY" in error_str or "secret" in error_str.lower(), \
        f"Error should mention SECRET_KEY, got: {error_str}"


@pytest.mark.integration
@pytest.mark.regression
def test_secret_key_allows_default_in_development():
    """
    REGRESSION: Default SECRET_KEY allowed in development (DEBUG=True)
    
    This test verifies that default SECRET_KEY is allowed when DEBUG=True,
    but a warning should be logged (we can't easily test the warning, but
    we can verify it doesn't raise an error).
    """
    original_debug = os.environ.get('DEBUG')
    original_secret = os.environ.get('SECRET_KEY')
    try:
        if 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        
        # Create settings with default key and DEBUG=True (should work with warning)
        from app.core.config import Settings
        settings = Settings(
            SECRET_KEY="your-secret-key-change-in-production",
            DEBUG=True
        )
        
        # Should not raise an error
        assert settings.SECRET_KEY == "your-secret-key-change-in-production"
        assert settings.DEBUG is True
        
    finally:
        # Restore environment
        if original_debug:
            os.environ['DEBUG'] = original_debug
        elif 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if original_secret:
            os.environ['SECRET_KEY'] = original_secret
        elif 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']


@pytest.mark.integration
@pytest.mark.regression
def test_secret_key_accepts_custom_value():
    """
    REGRESSION: Custom SECRET_KEY works in both production and development
    
    This test verifies that a custom (non-default) SECRET_KEY is accepted
    in both DEBUG=True and DEBUG=False modes.
    """
    original_debug = os.environ.get('DEBUG')
    original_secret = os.environ.get('SECRET_KEY')
    try:
        if 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        
        from app.core.config import Settings
        
        # Test with DEBUG=False (production)
        # Must provide non-default values for all security-sensitive settings
        settings_prod = Settings(
            SECRET_KEY="custom-secure-key-12345",
            DEBUG=False,
            DATABASE_URL="postgresql://user:secure_password@db:5432/database",
            MINIO_ACCESS_KEY="secure_minio_key",
            MINIO_SECRET_KEY="secure_minio_secret"
        )
        assert settings_prod.SECRET_KEY == "custom-secure-key-12345"
        assert settings_prod.DEBUG is False
        
        # Test with DEBUG=True (development)
        # In DEBUG mode, defaults are allowed (just warnings)
        settings_dev = Settings(
            SECRET_KEY="custom-secure-key-12345",
            DEBUG=True
        )
        assert settings_dev.SECRET_KEY == "custom-secure-key-12345"
        assert settings_dev.DEBUG is True
        
    finally:
        # Restore environment
        if original_debug:
            os.environ['DEBUG'] = original_debug
        elif 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if original_secret:
            os.environ['SECRET_KEY'] = original_secret
        elif 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']

