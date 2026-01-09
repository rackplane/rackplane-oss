#!/usr/bin/env python3
"""
Comprehensive Restore CLI for Datacenter Inventory Management System
Restores database, photos, and all metadata from a backup archive
"""

import sys
import os
import json
import tarfile
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db_url
from app.services.backup_service import BackupService
from app.core.config import settings


def get_uploads_directory() -> Path:
    """Get the uploads directory path"""
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_absolute():
        # If relative, make it relative to the app directory
        upload_dir = Path(__file__).parent / upload_dir
    return upload_dir


def extract_backup_archive(backup_path: Path, extract_dir: Path) -> dict:
    """
    Extract backup archive to temporary directory
    
    Returns:
        Dictionary with extracted file paths and metadata
    """
    print(f"📦 Extracting backup archive: {backup_path}")
    
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        'database_dump': None,
        'database_json': None,
        'metadata_json': None,
        'uploads_dir': None,
        'files_extracted': 0,
        'errors': []
    }
    
    try:
        with tarfile.open(backup_path, 'r:gz') as tar:
            # Extract all files
            tar.extractall(extract_dir)
            
            # Find database file (native dump or legacy json)
            db_dump_path = extract_dir / 'database.dump'
            db_json_path = extract_dir / 'database.json'
            
            if db_dump_path.exists():
                result['database_dump'] = db_dump_path
                print(f"   ✓ Found database.dump (Native)")
            elif db_json_path.exists():
                result['database_json'] = db_json_path
                print(f"   ✓ Found database.json (Legacy)")
            else:
                result['errors'].append("No database backup found (checked database.dump and database.json)")
            
            # Find metadata
            metadata_path = extract_dir / 'backup_metadata.json'
            if metadata_path.exists():
                result['metadata_json'] = metadata_path
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    print(f"   ✓ Backup date: {metadata.get('backup_date', 'Unknown')}")
                    print(f"   ✓ Database records: {metadata.get('database_records', 0):,}")
                    print(f"   ✓ Files: {metadata.get('files_count', 0):,}")
            
            # Check for uploads directory
            uploads_extract_dir = extract_dir / 'uploads'
            if uploads_extract_dir.exists():
                result['uploads_dir'] = uploads_extract_dir
                # Count files
                file_count = sum(1 for _ in uploads_extract_dir.rglob('*') if _.is_file())
                result['files_extracted'] = file_count
                print(f"   ✓ Extracted {file_count} files from uploads/")
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to extract archive: {str(e)}"
        print(f"✗ {error_msg}")
        result['errors'].append(error_msg)
        return result


def restore_database(db_json_path: Path, clear_existing: bool = False) -> dict:
    """Restore database from JSON backup"""
    print("\n📊 Restoring database...")
    
    db: Session = SessionLocal()
    try:
        # Load backup data
        with open(db_json_path) as f:
            backup_data = json.load(f)
        
        # Validate backup
        is_valid, errors = BackupService.validate_backup(backup_data)
        if not is_valid:
            print(f"✗ Backup validation failed:")
            for error in errors:
                print(f"   - {error}")
            return {'success': False, 'errors': errors}
        
        print("   ✓ Backup validation passed")
        
        # Import database
        stats = BackupService.import_database(db, backup_data, clear_existing=clear_existing)
        
        if stats.get('errors'):
            print(f"\n⚠️  Restore completed with {len(stats['errors'])} errors")
            for error in stats['errors']:
                print(f"   - {error}")
        else:
            print(f"\n✅ Database restore completed successfully!")
            print(f"   Tables imported: {stats.get('tables_imported', 0)}")
            print(f"   Records imported: {stats.get('total_records_imported', 0):,}")
        
        return {'success': len(stats.get('errors', [])) == 0, 'stats': stats}
        
    except Exception as e:
        error_msg = f"Failed to restore database: {str(e)}"
        print(f"✗ {error_msg}")
        return {'success': False, 'errors': [error_msg]}
    finally:
        db.close()


def restore_files(uploads_extract_dir: Path, target_uploads_dir: Path) -> dict:
    """Restore uploaded files to uploads directory"""
    print("\n📁 Restoring uploaded files...")
    
    result = {
        'files_restored': 0,
        'errors': []
    }
    
    try:
        # Create target directory if it doesn't exist
        target_uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files from extracted directory to target
        if uploads_extract_dir.exists():
            for file_path in uploads_extract_dir.rglob('*'):
                if file_path.is_file():
                    # Get relative path from uploads_extract_dir
                    rel_path = file_path.relative_to(uploads_extract_dir)
                    target_path = target_uploads_dir / rel_path
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, target_path)
                    result['files_restored'] += 1
            
            print(f"   ✓ Restored {result['files_restored']} files to {target_uploads_dir}")
        else:
            print("   ℹ No uploads directory in backup")
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to restore files: {str(e)}"
        print(f"✗ {error_msg}")
        result['errors'].append(error_msg)
        return result


def restore_from_archive(backup_path: Path, clear_existing: bool = False, skip_files: bool = False) -> dict:
    """
    Restore from backup archive (database + files)
    
    Args:
        backup_path: Path to backup archive (.tar.gz)
        clear_existing: If True, clear existing database before restore
        skip_files: If True, skip file restoration
    
    Returns:
        Dictionary with restore statistics
    """
    print("=" * 70)
    print("DATACENTER INVENTORY MANAGEMENT SYSTEM - RESTORE")
    print("=" * 70)
    print()
    
    if not backup_path.exists():
        print(f"✗ Backup file not found: {backup_path}")
        return {'success': False, 'errors': [f'Backup file not found: {backup_path}']}
    
    # Create temporary extraction directory
    extract_dir = Path('/tmp') / f'dcms_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    try:
        # Step 1: Extract archive
        print("Step 1: Extracting backup archive...")
        extract_result = extract_backup_archive(backup_path, extract_dir)
        
        if extract_result.get('errors'):
            print(f"\n✗ Extraction failed:")
            for error in extract_result['errors']:
                print(f"   - {error}")
            return {'success': False, 'errors': extract_result['errors']}
        
        # Step 2: Restore database
        if extract_result.get('database_dump'):
            # Native Restore
            print("\n📊 Restoring Native Database Dump...")
            from app.services.native_backup_service import NativeBackupService
            native_result = NativeBackupService.restore_dump(extract_result['database_dump'], clean=clear_existing)
            
            if not native_result.get('success'):
                return {'success': False, 'errors': [native_result.get('error', 'Unknown native restore error')]}
            
            print(f"   ✓ Native restore successful")
            if native_result.get('warnings'):
                print(f"   ⚠️ Warnings: {native_result['warnings']}")
                
        elif extract_result.get('database_json'):
            # Legacy JSON Restore
            db_result = restore_database(extract_result['database_json'], clear_existing=clear_existing)
            if not db_result.get('success'):
                return {'success': False, 'errors': db_result.get('errors', [])}
        else:
            print("\n✗ No database backup found in archive")
            return {'success': False, 'errors': ['No database backup found']}
        
        # Step 3: Restore files
        if not skip_files and extract_result.get('uploads_dir'):
            target_uploads_dir = get_uploads_directory()
            files_result = restore_files(extract_result['uploads_dir'], target_uploads_dir)
            if files_result.get('errors'):
                print(f"\n⚠️  File restoration had {len(files_result['errors'])} errors")
                for error in files_result['errors']:
                    print(f"   - {error}")
        elif skip_files:
            print("\n📁 Skipping file restoration (--skip-files specified)")
        else:
            print("\n📁 No files to restore")
        
        print("\n" + "=" * 70)
        print("✅ RESTORE COMPLETED")
        print("=" * 70)
        
        return {
            'success': True,
            'database_restored': True,
            'files_restored': extract_result.get('files_extracted', 0) if not skip_files else 0
        }
        
    finally:
        # Clean up extraction directory
        if extract_dir.exists():
            print(f"\n🧹 Cleaning up temporary files...")
            shutil.rmtree(extract_dir)
            print("   ✓ Cleanup complete")


def restore_from_json(json_path: Path, clear_existing: bool = False) -> dict:
    """Restore database from JSON file (database-only backup)"""
    print("=" * 70)
    print("DATACENTER INVENTORY MANAGEMENT SYSTEM - DATABASE RESTORE")
    print("=" * 70)
    print()
    
    if not json_path.exists():
        print(f"✗ Backup file not found: {json_path}")
        return {'success': False, 'errors': [f'Backup file not found: {json_path}']}
    
    result = restore_database(json_path, clear_existing=clear_existing)
    
    if result.get('success'):
        print("\n" + "=" * 70)
        print("✅ RESTORE COMPLETED")
        print("=" * 70)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Restore tool for Datacenter Inventory Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Restore from full backup archive
  python restore_cli.py restore backup.tar.gz
  
  # Restore and clear existing data
  python restore_cli.py restore backup.tar.gz --clear
  
  # Restore database only (skip files)
  python restore_cli.py restore backup.tar.gz --skip-files
  
  # Restore from JSON backup (database only)
  python restore_cli.py restore backup.json --clear
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument(
        'backup_file',
        type=str,
        help='Path to backup file (.tar.gz or .json)'
    )
    restore_parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing database before restore (⚠️ DANGEROUS!)'
    )
    restore_parser.add_argument(
        '--skip-files',
        action='store_true',
        help='Skip file restoration (database only)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'restore':
        backup_path = Path(args.backup_file)
        
        if not backup_path.exists():
            print(f"✗ Backup file not found: {backup_path}")
            sys.exit(1)
        
        # Determine backup type
        if backup_path.suffix == '.json':
            # Database-only JSON backup
            result = restore_from_json(backup_path, clear_existing=args.clear)
        elif backup_path.suffixes == ['.tar', '.gz'] or backup_path.suffix == '.gz':
            # Full archive backup
            result = restore_from_archive(backup_path, clear_existing=args.clear, skip_files=args.skip_files)
        elif backup_path.suffix == '.dump':
            # Native PostgreSQL dump
            result = restore_native_dump(backup_path, clear_existing=args.clear)
        else:
            print(f"✗ Unknown backup file format: {backup_path}")
            print("   Supported formats: .json (database only), .tar.gz (full archive), or .dump (native)")
            sys.exit(1)
        
        if not result.get('success'):
            sys.exit(1)


if __name__ == '__main__':
    main()

