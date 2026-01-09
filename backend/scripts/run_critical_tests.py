#!/usr/bin/env python3
"""
Run Critical Smoke Tests

This script runs the critical test suite that must pass after any system change.
These tests verify:
- Authentication and authorization
- Data integrity (duplicate prevention)
- Multi-tenancy isolation
- Basic CRUD operations
- Backup/restore functionality

Usage:
    python scripts/run_critical_tests.py
    python scripts/run_critical_tests.py --verbose
    python scripts/run_critical_tests.py --coverage
"""

import sys
import os
import subprocess
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def main():
    """Run critical tests."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run critical smoke tests that must pass after any system change"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage (faster)"
    )
    parser.add_argument(
        "-x", "--exitfirst",
        action="store_true",
        help="Exit on first failure"
    )
    parser.add_argument(
        "--tb",
        default="short",
        choices=["short", "long", "line", "no"],
        help="Traceback style"
    )
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd = ["python3", "-m", "pytest"]
    
    # Add markers
    cmd.extend(["-m", "critical"])
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
        cmd.append("-s")  # No capture - show server logs!
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    elif not args.no_cov:
        # Default: minimal coverage
        cmd.extend([
            "--cov=app",
            "--cov-report=term"
        ])
    
    # Add exit on first failure
    if args.exitfirst:
        cmd.append("-x")
    
    # Add traceback style
    cmd.extend(["--tb", args.tb])
    
    # Add test path
    cmd.append("tests/")
    
    print("=" * 80)
    print("CRITICAL SMOKE TESTS")
    print("=" * 80)
    print()
    print("These tests verify core system functionality:")
    print("  ✓ Authentication and authorization")
    print("  ✓ Data integrity (duplicate prevention)")
    print("  ✓ Multi-tenancy isolation")
    print("  ✓ Basic CRUD operations")
    print("  ✓ Backup/restore functionality")
    print()
    print("Running tests...")
    print("=" * 80)
    print()
    
    # Run pytest
    result = subprocess.run(cmd, cwd=backend_dir)
    
    print()
    print("=" * 80)
    if result.returncode == 0:
        print("✅ ALL CRITICAL TESTS PASSED")
        print("=" * 80)
        return 0
    else:
        print("❌ CRITICAL TESTS FAILED")
        print("=" * 80)
        print()
        print("These tests must pass before deploying changes!")
        print("Review the failures above and fix them before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

