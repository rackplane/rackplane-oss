#!/usr/bin/env python3
"""
Pre-commit hook to check migration safety.

This script validates that migrations don't accidentally drop critical
unique constraints without replacement.

Usage:
    python scripts/check_migration_safety.py <migration_file>
    python scripts/check_migration_safety.py  # Check all pending migrations
"""

import sys
import os
import re
from pathlib import Path

# Critical unique constraints that must not be dropped without replacement
CRITICAL_CONSTRAINTS = [
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
]

# Pattern to match any tenant-scoped unique constraint
TENANT_UNIQUE_PATTERN = re.compile(r'idx_\w+_\w+_tenant')


def check_migration_file(file_path: Path) -> list:
    """Check a single migration file for safety issues."""
    errors = []
    warnings = []
    
    if not file_path.exists():
        return [f"File not found: {file_path}"]
    
    content = file_path.read_text()
    
    # Check for drops of critical constraints
    for constraint in CRITICAL_CONSTRAINTS:
        # Look for any mention of dropping this constraint
        # This catches: drop_index(), drop_index_if_exists(), op.drop_index(), etc.
        drop_patterns = [
            re.compile(rf'drop_index[^)]*{re.escape(constraint)}', re.IGNORECASE),
            re.compile(rf'drop_index_if_exists[^)]*{re.escape(constraint)}', re.IGNORECASE),
            re.compile(rf'drop_constraint[^)]*{re.escape(constraint)}', re.IGNORECASE),
            re.compile(rf"['\"].*{re.escape(constraint)}.*['\"].*drop", re.IGNORECASE),
        ]
        
        dropped = False
        for pattern in drop_patterns:
            if pattern.search(content):
                dropped = True
                break
        
        # Also check if constraint name appears in a drop context
        if constraint in content:
            # Check if it's in a drop_index call (even with helper functions)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if constraint in line and ('drop' in line.lower() or 'drop_index' in line.lower()):
                    # Check if it's actually being dropped (not just referenced)
                    if 'drop_index' in line.lower() or 'drop_constraint' in line.lower():
                        dropped = True
                        break
        
        if dropped:
            # Check if it's replaced in the same upgrade() function
            # Extract the upgrade function content
            upgrade_match = re.search(r'def upgrade\(\)[^:]*:(.*?)(?=\n\ndef |\n\nclass |\Z)', content, re.DOTALL)
            if upgrade_match:
                upgrade_content = upgrade_match.group(1)
                
                # Check if constraint is recreated with unique=True
                # Look for create_index calls that recreate this constraint with unique=True
                replaced = False
                
                # Pattern 1: Direct create_index with constraint name and unique=True
                if re.search(rf'create_index[^)]*{re.escape(constraint)}[^)]*unique\s*=\s*True', upgrade_content, re.IGNORECASE | re.DOTALL):
                    replaced = True
                
                # Pattern 2: create_index_if_not_exists with constraint name and unique=True
                if re.search(rf'create_index_if_not_exists[^)]*{re.escape(constraint)}[^)]*unique\s*=\s*True', upgrade_content, re.IGNORECASE | re.DOTALL):
                    replaced = True
                
                # Pattern 3: op.create_index with constraint name and unique=True
                if re.search(rf'op\.create_index[^)]*{re.escape(constraint)}[^)]*unique\s*=\s*True', upgrade_content, re.IGNORECASE | re.DOTALL):
                    replaced = True
                
                # Pattern 4: Check if constraint appears after drop in same function with unique
                # Find the line where it's dropped
                lines = upgrade_content.split('\n')
                drop_line_idx = None
                for i, line in enumerate(lines):
                    if constraint in line and ('drop' in line.lower()):
                        drop_line_idx = i
                        break
                
                if drop_line_idx is not None:
                    # Check subsequent lines for recreation
                    for line in lines[drop_line_idx:drop_line_idx+20]:  # Check next 20 lines
                        if constraint in line and 'create_index' in line.lower() and 'unique' in line.lower() and 'True' in line:
                            replaced = True
                            break
                
                if not replaced:
                    errors.append(
                        f"❌ CRITICAL: Migration drops '{constraint}' without replacement!\n"
                        f"   File: {file_path.name}\n"
                        f"   This unique constraint is critical for data integrity.\n"
                        f"   You must recreate it immediately in the same upgrade() function with unique=True.\n"
                        f"   See backend/alembic/MIGRATION_SAFETY_GUIDE.md for details."
                    )
    
    # Check for any tenant-scoped unique constraint drops
    tenant_drops = re.findall(
        r'(drop_index|drop_constraint).*?(idx_\w+_\w+_tenant)',
        content,
        re.IGNORECASE
    )
    
    for drop_op, constraint_name in tenant_drops:
        if constraint_name not in CRITICAL_CONSTRAINTS:
            # Check if it's replaced
            upgrade_match = re.search(r'def upgrade\(\)[^}]*?}', content, re.DOTALL)
            if upgrade_match:
                upgrade_content = upgrade_match.group(0)
                if constraint_name not in upgrade_content.replace(drop_op, ''):
                    warnings.append(
                        f"⚠️  WARNING: Migration drops tenant-scoped constraint '{constraint_name}'\n"
                        f"   Ensure this is intentional and replaced if it's a unique constraint."
                    )
    
    # Check downgrade() function exists and restores critical constraints
    if 'def downgrade()' in content:
        downgrade_match = re.search(r'def downgrade\(\)[^}]*?}', content, re.DOTALL)
        if downgrade_match:
            downgrade_content = downgrade_match.group(0)
            
            # Check if any dropped critical constraints are restored in downgrade
            for constraint in CRITICAL_CONSTRAINTS:
                if constraint in content.replace('def downgrade()', ''):
                    if f'drop_index.*{constraint}' in content or f'drop_constraint.*{constraint}' in content:
                        if constraint not in downgrade_content:
                            warnings.append(
                                f"⚠️  WARNING: '{constraint}' is dropped but not restored in downgrade()\n"
                                f"   Ensure downgrade() can properly rollback this change."
                            )
    else:
        warnings.append(
            "⚠️  WARNING: No downgrade() function found.\n"
            "   Consider adding one for safe rollbacks."
        )
    
    return errors, warnings


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Check specific file(s)
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Check all migration files in versions directory
        versions_dir = Path(__file__).parent.parent / 'alembic' / 'versions'
        if not versions_dir.exists():
            print(f"❌ Versions directory not found: {versions_dir}")
            sys.exit(1)
        files = list(versions_dir.glob('*.py'))
        files = [f for f in files if f.name != '__init__.py']
    
    all_errors = []
    all_warnings = []
    
    for file_path in files:
        if not file_path.is_file():
            continue
        
        errors, warnings = check_migration_file(file_path)
        
        if errors or warnings:
            print(f"\n📄 Checking: {file_path.name}")
            print("=" * 80)
            
            if errors:
                all_errors.extend(errors)
                for error in errors:
                    print(error)
            
            if warnings:
                all_warnings.extend(warnings)
                for warning in warnings:
                    print(warning)
    
    # Summary
    print("\n" + "=" * 80)
    if all_errors:
        print(f"❌ Found {len(all_errors)} CRITICAL error(s)")
        print("\nThese must be fixed before committing!")
        sys.exit(1)
    elif all_warnings:
        print(f"⚠️  Found {len(all_warnings)} warning(s)")
        print("Please review these before committing.")
        sys.exit(0)
    else:
        print("✅ No safety issues found")
        sys.exit(0)


if __name__ == '__main__':
    main()

