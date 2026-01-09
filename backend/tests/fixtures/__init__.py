"""
Test fixtures for RackPlane test suite.

This package contains reusable pytest fixtures for testing.
"""

# Import fixtures so pytest can discover them
try:
    from . import demo_database  # noqa: F401
except ImportError:
    pass

