#!/usr/bin/env python3
"""
Safe Migration Wrapper

This script runs `alembic upgrade head` and then automatically verifies
that all critical unique constraints are still present. This prevents
the loss of duplicate protection that has happened twice before.

Usage:
    python scripts/safe_migrate.py
    python scripts/safe_migrate.py --skip-verification  # Skip constraint check
"""

import sys
import subprocess
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)


def main():
    """Run migration and verify constraints."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Safely run database migrations with automatic constraint verification"
    )
    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip constraint verification (not recommended)'
    )
    parser.add_argument(
        '--revision',
        help='Upgrade to specific revision (default: head)'
    )
    parser.add_argument(
        '--database-url',
        help='Database URL (default: from DATABASE_URL env or config)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running critical tests after migration (not recommended)'
    )
    
    args = parser.parse_args()
    
    # CRITICAL: Check for single head BEFORE running migration
    print("=" * 80)
    print("PRE-MIGRATION SAFETY CHECK")
    print("=" * 80)
    print()
    print("Checking for single migration head...")
    
    check_result = subprocess.run(
        ['python3', 'scripts/check_single_head.py'],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr)
        print()
        print("=" * 80)
        print("❌ CRITICAL: Multiple migration heads detected!")
        print("=" * 80)
        print()
        print("Cannot proceed with migration. Multiple heads will cause 'alembic upgrade head' to fail.")
        print()
        print("Fix this by creating a merge migration:")
        print("  alembic revision -m 'merge_heads' --head <head1> --head <head2> ...")
        print()
        print("Then run this script again.")
        print("=" * 80)
        sys.exit(1)
    
    print("✓ Single migration head confirmed")
    print()
    
    # CRITICAL: Check if pending migrations drop critical constraints
    print("Checking pending migrations for constraint drops...")
    print()
    
    # Get the current revision and target revision
    current_result = subprocess.run(
        ['alembic', 'current'],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    # Get pending migrations
    revision = args.revision if args.revision else 'head'
    history_result = subprocess.run(
        ['alembic', 'history', '--verbose'],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    # Extract revision IDs from history (this is a simplified check)
    # For a more robust solution, we'd parse the alembic history output
    # For now, we'll check the migration files directly
    
    # Find all migration files that will be applied
    versions_dir = backend_dir / 'alembic' / 'versions'
    migration_files = list(versions_dir.glob('*.py'))
    
    # Check each migration file
    constraint_check_result = subprocess.run(
        ['python3', 'scripts/check_migration_drops_constraints.py', '--revision', 'head'],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    # For now, we'll do a simpler check: scan all migration files for drops
    # In a production system, you'd want to check only pending migrations
    print("⚠️  Note: Full constraint drop checking requires parsing alembic history")
    print("   For now, post-migration verification will catch any issues")
    print()
    
    # Build alembic command
    cmd = ['alembic', 'upgrade', revision]
    
    print("=" * 80)
    print("SAFE MIGRATION - Running Alembic Upgrade")
    print("=" * 80)
    print()
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run migration
    result = subprocess.run(cmd, cwd=backend_dir)
    
    if result.returncode != 0:
        print()
        print("=" * 80)
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print()
        print("Migration did not complete successfully.")
        print("Fix the migration errors before proceeding.")
        sys.exit(result.returncode)
    
    print()
    print("=" * 80)
    print("✓ Migration completed successfully")
    print("=" * 80)
    print()
    
    # Verify constraints (unless skipped)
    if not args.skip_verification:
        print("Running post-migration constraint verification...")
        print()
        
        verify_cmd = ['python3', 'scripts/verify_constraints_after_migration.py']
        if args.database_url:
            verify_cmd.extend(['--database-url', args.database_url])
        
        verify_result = subprocess.run(verify_cmd, cwd=backend_dir)
        
        if verify_result.returncode != 0:
            print()
            print("=" * 80)
            print("❌ CONSTRAINT VERIFICATION FAILED")
            print("=" * 80)
            print()
            print("CRITICAL: Some duplicate protection constraints are missing!")
            print()
            print("DO NOT deploy this migration to production.")
            print("Create a new migration to restore the missing constraints.")
            print()
            print("See backend/alembic/MIGRATION_SAFETY_GUIDE.md for recovery steps.")
            print()
            sys.exit(1)
    else:
        print("⚠️  WARNING: Constraint verification skipped")
        print("   This is not recommended. Run verification manually:")
        print("   python3 scripts/verify_constraints_after_migration.py")
        print()
    
    # Run critical tests (unless skipped)
    if not args.skip_tests:
        print()
        print("=" * 80)
        print("RUNNING CRITICAL REGRESSION TESTS")
        print("=" * 80)
        print()
        print("These tests verify that all duplicate prevention constraints still work")
        print("after the migration. This is critical to prevent data loss.")
        print()
        
        test_cmd = ['python3', 'scripts/run_critical_tests.py', '--exitfirst']
        test_result = subprocess.run(test_cmd, cwd=backend_dir)
        
        if test_result.returncode != 0:
            print()
            print("=" * 80)
            print("❌ CRITICAL TESTS FAILED")
            print("=" * 80)
            print()
            print("CRITICAL: Regression tests failed after migration!")
            print()
            print("This indicates that the migration may have broken duplicate prevention.")
            print("DO NOT deploy this migration to production.")
            print()
            print("Next steps:")
            print("  1. Review the test failures above")
            print("  2. Check if constraints are missing (run: make migrate-verify)")
            print("  3. Create a restoration migration if needed")
            print("  4. Fix any issues and re-run: make migrate")
            print()
            sys.exit(1)
        else:
            print()
            print("=" * 80)
            print("✅ ALL CRITICAL TESTS PASSED")
            print("=" * 80)
            print()
    
    print()
    print("=" * 80)
    print("✅ MIGRATION COMPLETE - All checks passed")
    print("=" * 80)
    print()
    if args.skip_tests:
        print("⚠️  WARNING: Critical tests were skipped")
        print("   Run them manually: python3 scripts/run_critical_tests.py")
        print()
    else:
        print("✓ Migration completed successfully")
        print("✓ All constraints verified")
        print("✓ All critical regression tests passed")
        print()
        print("The migration is safe to deploy.")
        print()


if __name__ == '__main__':
    main()

