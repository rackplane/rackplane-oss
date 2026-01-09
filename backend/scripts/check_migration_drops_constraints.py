#!/usr/bin/env python3
"""
Pre-Migration Constraint Drop Checker

This script scans migration files for operations that would drop critical
unique constraints. It BLOCKS migrations that attempt to drop these constraints
without immediate replacement.

CRITICAL: This prevents the 10+ times constraints have been accidentally dropped.

Usage:
    python scripts/check_migration_drops_constraints.py <migration_file>
    python scripts/check_migration_drops_constraints.py --revision <revision_id>
"""

import sys
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

# Critical unique constraints that MUST NOT be dropped
CRITICAL_CONSTRAINTS = {
    'idx_users_username_tenant',
    'idx_racks_code_tenant',
    'idx_storage_containers_name_tenant',
    'idx_storage_containers_barcode_tenant',
    'idx_assets_tag_tenant',
    'idx_assets_serial_tenant',
    'idx_assets_hostname_tenant',
    'idx_asset_types_name_tenant',
    'idx_datacenters_name_tenant',
    'idx_datacenters_code_tenant',
    'idx_network_cables_serial_tenant',
    'idx_environmental_sensors_sensor_id_tenant',
}

# Pattern to match drop_index operations
DROP_INDEX_PATTERNS = [
    r"drop_index\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
    r"drop_index_if_exists\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
    r"DROP\s+INDEX\s+(?:IF\s+EXISTS\s+)?(idx_\w+_tenant)",
    r"op\.drop_index\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
]

# Pattern to match create_index operations (to check for replacement)
CREATE_INDEX_PATTERNS = [
    r"create_index\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
    r"create_index_if_not_exists\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(idx_\w+_tenant)",
    r"op\.create_index\s*\([^)]*['\"](idx_\w+_tenant)['\"]",
]


def find_constraint_drops(content: str) -> List[str]:
    """Find all critical constraints that are being dropped."""
    dropped = []
    
    for pattern in DROP_INDEX_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            constraint_name = match.group(1)
            if constraint_name in CRITICAL_CONSTRAINTS:
                dropped.append(constraint_name)
    
    return list(set(dropped))  # Remove duplicates


def find_constraint_creates(content: str) -> List[str]:
    """Find all critical constraints that are being created."""
    created = []
    
    for pattern in CREATE_INDEX_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            constraint_name = match.group(1)
            if constraint_name in CRITICAL_CONSTRAINTS:
                created.append(constraint_name)
    
    return list(set(created))


def check_migration_file(file_path: Path) -> Tuple[bool, List[str], List[str]]:
    """
    Check if a migration file drops critical constraints.
    
    Returns:
        (is_safe, dropped_constraints, created_constraints)
    """
    if not file_path.exists():
        return False, [], []
    
    content = file_path.read_text()
    
    dropped = find_constraint_drops(content)
    created = find_constraint_creates(content)
    
    # Check if all dropped constraints are recreated
    dropped_set = set(dropped)
    created_set = set(created)
    
    # Migration is safe if:
    # 1. No critical constraints are dropped, OR
    # 2. All dropped constraints are recreated in the same migration
    is_safe = len(dropped) == 0 or dropped_set.issubset(created_set)
    
    return is_safe, dropped, created


def get_migration_file(revision: str) -> Path:
    """Get the migration file path for a given revision."""
    backend_dir = Path(__file__).parent.parent
    versions_dir = backend_dir / 'alembic' / 'versions'
    
    # Find migration file by revision
    for file_path in versions_dir.glob('*.py'):
        content = file_path.read_text()
        if f"revision: str = '{revision}'" in content or f'revision: str = "{revision}"' in content:
            return file_path
    
    raise FileNotFoundError(f"Migration file for revision {revision} not found")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check if a migration drops critical unique constraints"
    )
    parser.add_argument(
        'migration_file',
        nargs='?',
        help='Path to migration file to check'
    )
    parser.add_argument(
        '--revision',
        help='Revision ID to check (instead of file path)'
    )
    
    args = parser.parse_args()
    
    if args.revision:
        try:
            migration_file = get_migration_file(args.revision)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
    elif args.migration_file:
        migration_file = Path(args.migration_file)
    else:
        print("❌ Error: Must provide either migration_file or --revision")
        sys.exit(1)
    
    is_safe, dropped, created = check_migration_file(migration_file)
    
    if not is_safe:
        print("=" * 80)
        print("❌ CRITICAL: Migration drops unique constraints without replacement!")
        print("=" * 80)
        print()
        print(f"Migration file: {migration_file}")
        print()
        print("DROPPED constraints (CRITICAL - will allow duplicate data):")
        for constraint in dropped:
            print(f"  • {constraint}")
        print()
        if created:
            print("CREATED constraints:")
            for constraint in created:
                print(f"  • {constraint}")
            print()
            missing = set(dropped) - set(created)
            if missing:
                print("MISSING replacements (must be created in same migration):")
                for constraint in missing:
                    print(f"  • {constraint}")
                print()
        else:
            print("NO constraints created - all dropped constraints are missing!")
            print()
        print("=" * 80)
        print("BLOCKING MIGRATION")
        print("=" * 80)
        print()
        print("This migration will NOT be allowed to run.")
        print()
        print("To fix:")
        print("  1. Add create_index() calls for all dropped constraints")
        print("  2. Ensure new indexes are UNIQUE (not just regular indexes)")
        print("  3. Re-run this check")
        print()
        print("See backend/alembic/MIGRATION_SAFETY_GUIDE.md for details.")
        print()
        sys.exit(1)
    else:
        if dropped:
            print("✓ Migration drops constraints but recreates them:")
            for constraint in dropped:
                print(f"  • {constraint} (recreated)")
        else:
            print("✓ Migration does not drop any critical constraints")
        sys.exit(0)


if __name__ == '__main__':
    main()

