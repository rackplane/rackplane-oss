#!/usr/bin/env python3
"""
Comprehensive Backup CLI for Datacenter Inventory Management System
Backs up database, photos, and all metadata to a single archive file
"""

import sys
import os
import json
import tarfile
import argparse
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


def collect_file_paths(uploads_dir: Path) -> list:
    """Collect all file paths from uploads directory"""
    file_paths = []
    if uploads_dir.exists():
        for root, dirs, files in os.walk(uploads_dir):
            for file in files:
                file_path = Path(root) / file
                # Get relative path from uploads directory
                rel_path = file_path.relative_to(uploads_dir)
                file_paths.append((file_path, rel_path))
    return file_paths


from app.services.native_backup_service import NativeBackupService

def create_backup_archive(output_path: Path, include_files: bool = True, native: bool = True) -> dict:
    """
    Create a complete backup archive with database and files
    
    Args:
        output_path: Path where the backup archive will be created
        include_files: Whether to include uploaded files (photos, etc.)
        native: If True, use native PostgreSQL dump (pg_dump -Fc). If False, use legacy JSON.
    
    Returns:
        Dictionary with backup metadata and statistics
    """
    print("=" * 70)
    print("DATACENTER INVENTORY MANAGEMENT SYSTEM - COMPREHENSIVE BACKUP")
    print("=" * 70)
    print()
    
    stats = {
        'backup_date': datetime.utcnow().isoformat(),
        'database_records': 0,
        'files_backed_up': 0,
        'total_file_size': 0,
        'archive_size': 0,
        'native_backup': native,
        'errors': []
    }
    
    # Step 1: Export database
    print("📊 Step 1: Exporting database...")
    
    db_dump_path = None
    backup_data = {} # For legacy metadata or if we want to include summary
    
    try:
        if native:
            print("   Using Native PostgreSQL Dump (pg_dump)...")
            # Create a temp file for the dump
            db_dump_path = Path('/tmp') / f'db_dump_{datetime.now().strftime("%Y%m%d_%H%M%S")}.dump'
            result = NativeBackupService.create_dump(db_dump_path)
            
            if not result.get('success'):
                raise Exception(result.get('error', 'Unknown native backup error'))
                
            stats['database_size'] = result.get('size_bytes', 0)
            print(f"✓ Native dump created: {stats['database_size'] / 1024 / 1024:.2f} MB")
            
        else:
            # Legacy JSON Export
            print("   Using Legacy JSON Export...")
            db: Session = SessionLocal()
            try:
                backup_data = BackupService.export_database(db)
                
                # Count total records
                for table_name, table_data in backup_data.get('tables', {}).items():
                    stats['database_records'] += table_data.get('count', 0)
                
                print(f"✓ Database exported: {stats['database_records']} total records")
            finally:
                db.close()
                
    except Exception as e:
        error_msg = f"Failed to export database: {str(e)}"
        print(f"✗ {error_msg}")
        stats['errors'].append(error_msg)
        if db_dump_path and db_dump_path.exists():
            try:
                db_dump_path.unlink()
            except:
                pass
        return stats
    
    # Step 2: Collect files if requested
    file_list = []
    if include_files:
        print("\n📁 Step 2: Collecting uploaded files...")
        uploads_dir = get_uploads_directory()
        print(f"   Uploads directory: {uploads_dir}")
        
        if uploads_dir.exists():
            file_paths = collect_file_paths(uploads_dir)
            stats['files_backed_up'] = len(file_paths)
            
            for file_path, rel_path in file_paths:
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    stats['total_file_size'] += file_size
                    file_list.append((file_path, rel_path))
            
            print(f"✓ Found {stats['files_backed_up']} files ({stats['total_file_size'] / 1024 / 1024:.2f} MB)")
        else:
            print(f"⚠ Uploads directory does not exist: {uploads_dir}")
    else:
        print("\n📁 Step 2: Skipping file backup (--database-only specified)")
    
    # Step 3: Create archive
    print(f"\n📦 Step 3: Creating backup archive...")
    print(f"   Output: {output_path}")
    
    try:
        with tarfile.open(output_path, 'w:gz') as tar:
            
            if native and db_dump_path:
                # Add Native Dump
                tar.add(db_dump_path, arcname='database.dump')
                print("   ✓ Added database.dump (Native PostgreSQL)")
                
                # Cleanup dump file after adding
                if db_dump_path.exists():
                    db_dump_path.unlink()
            else:
                # Add Legacy JSON
                db_json_path = Path('/tmp') / f'db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                
                # Add backup metadata to JSON before saving
                backup_data['metadata']['backup_type'] = 'full' if include_files else 'database_only'
                backup_data['metadata']['includes_files'] = include_files
                backup_data['metadata']['backup_tool'] = 'backup_cli.py'
                
                with open(db_json_path, 'w') as f:
                    json.dump(backup_data, f, indent=2)
                
                tar.add(db_json_path, arcname='database.json')
                print("   ✓ Added database.json")
                
                if db_json_path.exists():
                    db_json_path.unlink()
            
            # Add files if any
            if file_list:
                for file_path, rel_path in file_list:
                    tar.add(file_path, arcname=f'uploads/{rel_path}')
                print(f"   ✓ Added {len(file_list)} files to archive")
            
            # Add backup metadata
            metadata = {
                'backup_date': stats['backup_date'],
                'database_records': stats.get('database_records', 0),
                'files_count': stats['files_backed_up'],
                'total_file_size_bytes': stats['total_file_size'],
                'includes_files': include_files,
                'native_backup': native,
                'version': '2.0' if native else '1.0'
            }
            metadata_json_path = Path('/tmp') / f'metadata_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(metadata_json_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            tar.add(metadata_json_path, arcname='backup_metadata.json')
            print("   ✓ Added backup_metadata.json")
        
        # Clean up temp files
        if metadata_json_path.exists():
            metadata_json_path.unlink()
        
        # Get archive size
        stats['archive_size'] = output_path.stat().st_size
        
        print(f"\n✅ Backup completed successfully!")
        print(f"   Archive: {output_path}")
        print(f"   Size: {stats['archive_size'] / 1024 / 1024:.2f} MB")
        print(f"   Database records: {stats['database_records']}")
        print(f"   Files: {stats['files_backed_up']}")
        
    except Exception as e:
        error_msg = f"Failed to create archive: {str(e)}"
        print(f"✗ {error_msg}")
        stats['errors'].append(error_msg)
    
    return stats


def export_database_only(output_path: Path) -> dict:
    """Export only database to JSON file"""
    print("=" * 70)
    print("DATACENTER INVENTORY MANAGEMENT SYSTEM - DATABASE EXPORT")
    print("=" * 70)
    print()
    
    print("📊 Exporting database...")
    db: Session = SessionLocal()
    try:
        backup_data = BackupService.export_database(db)
        
        with open(output_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        file_size = output_path.stat().st_size
        print(f"\n✅ Database exported successfully!")
        print(f"   File: {output_path}")
        print(f"   Size: {file_size / 1024 / 1024:.2f} MB")
        
        return {'success': True, 'file': str(output_path), 'size': file_size}
        
    except Exception as e:
        print(f"✗ Failed to export database: {str(e)}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()


def get_backup_summary(backup_path: Path) -> dict:
    """Get summary of a backup archive"""
    if not backup_path.exists():
        print(f"✗ Backup file not found: {backup_path}")
        return {}
    
    print(f"📋 Analyzing backup: {backup_path}")
    
    try:
        with tarfile.open(backup_path, 'r:gz') as tar:
            # Check for metadata file
            metadata_member = None
            for member in tar.getmembers():
                if member.name == 'backup_metadata.json':
                    metadata_member = member
                    break
            
            if metadata_member:
                metadata_file = tar.extractfile(metadata_member)
                metadata = json.load(metadata_file)
                print("\n📊 Backup Summary:")
                print(f"   Backup Date: {metadata.get('backup_date', 'Unknown')}")
                print(f"   Database Records: {metadata.get('database_records', 0):,}")
                print(f"   Files: {metadata.get('files_count', 0):,}")
                print(f"   Total File Size: {metadata.get('total_file_size_bytes', 0) / 1024 / 1024:.2f} MB")
                print(f"   Includes Files: {metadata.get('includes_files', False)}")
                return metadata
            else:
                # Try to read database.json directly
                db_member = None
                for member in tar.getmembers():
                    if member.name == 'database.json':
                        db_member = member
                        break
                
                if db_member:
                    db_file = tar.extractfile(db_member)
                    backup_data = json.load(db_file)
                    summary = BackupService.get_backup_summary(backup_data)
                    print("\n📊 Backup Summary:")
                    print(f"   Backup Date: {summary.get('backup_date', 'Unknown')}")
                    print(f"   Total Records: {summary.get('total_records', 0):,}")
                    print(f"   Tables: {summary.get('total_tables', 0)}")
                    return summary
                else:
                    print("✗ Could not find backup metadata or database.json in archive")
                    return {}
                    
    except Exception as e:
        print(f"✗ Failed to read backup: {str(e)}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description='Backup tool for Datacenter Inventory Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create full backup with auto-generated timestamp filename
  python backup_cli.py export
  # Creates: dcms_backup_2025-11-27_14-30-45.tar.gz
  
  # Create backup in specific directory (auto-generates filename)
  python backup_cli.py export --output /backups/
  # Creates: /backups/dcms_backup_2025-11-27_14-30-45.tar.gz
  
  # Create backup with custom filename (still recommended to include timestamp)
  python backup_cli.py export --output /backups/my_backup.tar.gz
  
  # Create database-only backup
  python backup_cli.py export --database-only
  # Creates: dcms_backup_2025-11-27_14-30-45.json
  
  # View backup summary
  python backup_cli.py summary dcms_backup_2025-11-27_14-30-45.tar.gz
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export database and/or files')
    export_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: auto-generated)'
    )
    export_parser.add_argument(
        '--database-only',
        action='store_true',
        help='Export only database (JSON format), skip files'
    )
    export_parser.add_argument(
        '--native',
        action='store_true',
        help='Export native PostgreSQL dump (preserves exact IDs/schema)'
    )
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='View backup summary')
    summary_parser.add_argument(
        'backup_file',
        type=str,
        help='Path to backup file'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'export':
        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        if args.output:
            output_path = Path(args.output)
            # If output is a directory, generate filename inside it
            if output_path.is_dir() or (not output_path.suffix and not output_path.exists()):
                # Treat as directory, generate filename
                if args.native:
                    output_path = output_path / f'dcms_native_{timestamp}.dump'
                elif args.database_only:
                    output_path = output_path / f'dcms_backup_{timestamp}.json'
                else:
                    output_path = output_path / f'dcms_backup_{timestamp}.tar.gz'
            # If output doesn't have extension and looks like a directory path, add filename
            elif not output_path.suffix:
                if args.native:
                    output_path = output_path / f'dcms_native_{timestamp}.dump'
                elif args.database_only:
                    output_path = output_path / f'dcms_backup_{timestamp}.json'
                else:
                    output_path = output_path / f'dcms_backup_{timestamp}.tar.gz'
        else:
            # Auto-generate filename with timestamp
            if args.native:
                output_path = Path(f'dcms_native_{timestamp}.dump')
            elif args.database_only:
                output_path = Path(f'dcms_backup_{timestamp}.json')
            else:
                output_path = Path(f'dcms_backup_{timestamp}.tar.gz')
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.native:
            if args.database_only:
                print("⚠ Warning: --database-only is implied with --native")
            result = export_native_backup(output_path)
            if not result.get('success'):
                sys.exit(1)
        elif args.database_only:
            result = export_database_only(output_path)
            if not result.get('success'):
                sys.exit(1)
        else:
            result = create_backup_archive(output_path, include_files=True)
            if result.get('errors'):
                sys.exit(1)
    
    elif args.command == 'summary':
        backup_path = Path(args.backup_file)
        if not backup_path.exists():
            print(f"✗ Backup file not found: {backup_path}")
            sys.exit(1)
        
        summary = get_backup_summary(backup_path)
        if not summary:
            sys.exit(1)


if __name__ == '__main__':
    main()

