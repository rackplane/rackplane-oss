#!/usr/bin/env python3
"""
Check for Single Migration Head

This script verifies that there is only one migration head.
Multiple heads indicate a broken migration chain that needs to be merged.

Usage:
    python scripts/check_single_head.py
"""
import sys
import subprocess
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)


def check_single_head():
    """Check that there is only one migration head."""
    try:
        result = subprocess.run(
            ["alembic", "heads"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        # Parse heads from output
        # Heads are lines like: "revision_id (head)"
        heads = []
        for line in output.split('\n'):
            line = line.strip()
            # Skip warnings and info messages
            if not line or line.startswith('WARN') or line.startswith('INFO') or line.startswith('Generating'):
                continue
            # Look for lines with "(head)" marker
            if '(head)' in line:
                # Extract revision ID (first word before space)
                parts = line.split()
                if parts:
                    heads.append(parts[0])
        
        if len(heads) > 1:
            print("=" * 80)
            print("❌ ERROR: Multiple migration heads detected!")
            print("=" * 80)
            print()
            print(f"Found {len(heads)} heads:")
            for head in heads:
                print(f"  - {head}")
            print()
            print("This should NEVER happen. The migration chain must have a single head.")
            print()
            print("To fix this, create a merge migration:")
            print(f"  alembic revision -m 'merge_heads' --head {' --head '.join(heads)}")
            print()
            print("Then commit the merge migration.")
            print("=" * 80)
            return False
        elif len(heads) == 1:
            print(f"✓ Single migration head: {heads[0]}")
            return True
        else:
            print("⚠️  WARNING: No migration heads found (empty migration history?)")
            return True
            
    except subprocess.TimeoutExpired:
        print("❌ ERROR: Migration check timed out")
        return False
    except Exception as e:
        print(f"❌ ERROR: Failed to check migration heads: {e}")
        return False


if __name__ == '__main__':
    success = check_single_head()
    sys.exit(0 if success else 1)

