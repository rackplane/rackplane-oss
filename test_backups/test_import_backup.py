#!/usr/bin/env python3
"""
Test script to import backup files for local testing.

Usage:
    python test_import_backup.py [--full|--json] [--clear-existing]
"""

import sys
import os
import argparse
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import requests
from requests.auth import HTTPBasicAuth

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "ChangeMe123!")

TEST_BACKUP_DIR = Path(__file__).parent
FULL_BACKUP = TEST_BACKUP_DIR / "dcms_backup_2025-11-28_20-50-30.tar.gz"
JSON_BACKUP = TEST_BACKUP_DIR / "dcms_backup_clean_2025-11-29_06-42-40.json"


def get_auth_token():
    """Get authentication token."""
    response = requests.post(
        f"{API_URL}/api/v1/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        raise Exception(f"Failed to authenticate: {response.text}")
    return response.json()["access_token"]


def import_full_backup(backup_path: Path, clear_existing: bool = False, skip_files: bool = False):
    """Import a full backup archive (.tar.gz)."""
    print(f"Importing full backup: {backup_path.name}")
    print(f"  Clear existing: {clear_existing}")
    print(f"  Skip files: {skip_files}")
    
    token = get_auth_token()
    
    with open(backup_path, "rb") as f:
        files = {"file": (backup_path.name, f, "application/gzip")}
        params = {
            "clear_existing": str(clear_existing).lower(),
            "skip_files": str(skip_files).lower()
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{API_URL}/api/v1/backup/import-archive",
            files=files,
            params=params,
            headers=headers
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Import successful!")
        if "stats" in result:
            stats = result["stats"]
            print(f"   Tables imported: {stats.get('tables_imported', 0)}")
            print(f"   Records imported: {stats.get('total_records_imported', 0)}")
        return True
    else:
        print(f"❌ Import failed: {response.status_code}")
        print(f"   {response.text}")
        return False


def import_json_backup(backup_path: Path, clear_existing: bool = False):
    """Import a JSON backup."""
    print(f"Importing JSON backup: {backup_path.name}")
    print(f"  Clear existing: {clear_existing}")
    
    token = get_auth_token()
    
    with open(backup_path, "rb") as f:
        files = {"file": (backup_path.name, f, "application/json")}
        params = {"clear_existing": str(clear_existing).lower()}
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{API_URL}/api/v1/backup/import",
            files=files,
            params=params,
            headers=headers
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Import successful!")
        if "stats" in result:
            stats = result["stats"]
            print(f"   Tables imported: {stats.get('tables_imported', 0)}")
            print(f"   Records imported: {stats.get('total_records_imported', 0)}")
        return True
    else:
        print(f"❌ Import failed: {response.status_code}")
        print(f"   {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Import backup files for testing")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Import full backup archive (.tar.gz)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Import JSON backup"
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear all existing data before importing"
    )
    parser.add_argument(
        "--skip-files",
        action="store_true",
        help="Skip restoring uploaded files (full backup only)"
    )
    
    args = parser.parse_args()
    
    if not args.full and not args.json:
        parser.print_help()
        print("\nError: Must specify --full or --json")
        sys.exit(1)
    
    if args.full:
        if not FULL_BACKUP.exists():
            print(f"❌ Full backup file not found: {FULL_BACKUP}")
            sys.exit(1)
        success = import_full_backup(FULL_BACKUP, args.clear_existing, args.skip_files)
    else:
        if not JSON_BACKUP.exists():
            print(f"❌ JSON backup file not found: {JSON_BACKUP}")
            sys.exit(1)
        success = import_json_backup(JSON_BACKUP, args.clear_existing)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

