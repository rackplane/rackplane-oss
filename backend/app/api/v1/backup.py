# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Database Backup and Restore API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_super_admin
from app.models.user import User
from app.services.backup_service import BackupService
from backup_cli import create_backup_archive
from restore_cli import restore_from_archive

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/export", summary="Export database")
async def export_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Export database to JSON format.

    - Super admins: Export ALL tenants' data (full system backup)
    - Regular users: Export only their tenant's data (via tenant filter)
    """
    try:
        # Super admins can export all data (skip tenant filtering)
        # Regular users export only their tenant's data (tenant filtering applied)
        skip_tenant_filter = current_user.is_super_admin
        backup_data = BackupService.export_database(db, skip_tenant_filter=skip_tenant_filter)

        # Add export metadata
        metadata = backup_data.setdefault("metadata", {})
        metadata["exported_by"] = current_user.username
        metadata["export_timestamp"] = datetime.utcnow().isoformat()

        if current_user.is_super_admin:
            metadata["scope"] = "full_system"
            metadata["exported_by_super_admin"] = True
        else:
            metadata["scope"] = "tenant"
            metadata["tenant_id"] = current_user.tenant_id

        return backup_data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export database: {str(e)}",
        )


@router.post("/import", summary="Import database from backup")
async def import_database(
    file: UploadFile = File(...),
    clear_existing: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Import database from a backup JSON file.

    Args:
        file: The backup JSON file to import
        clear_existing: If True, delete all existing data before importing (WARNING: destructive!)

    Returns:
        Import statistics including number of records imported and any errors
    """
    try:
        # Read and parse the uploaded file
        contents = await file.read()

        try:
            backup_data = json.loads(contents)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON file: {str(e)}"
            )

        # Validate backup data
        is_valid, errors = BackupService.validate_backup(backup_data)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backup file: {', '.join(errors)}",
            )

        # Determine scope from metadata (may be missing for older backups)
        metadata = backup_data.get("metadata", {})
        backup_scope = metadata.get("scope", "unknown")
        backup_tenant_id = metadata.get("tenant_id")

        # Permission checks
        if current_user.is_super_admin:
            # Super admin can import anything
            if backup_scope == "tenant" and backup_tenant_id:
                stats = BackupService.import_database(db, backup_data, clear_existing)
            else:
                stats = BackupService.import_database(db, backup_data, clear_existing)
        else:
            # Regular user restrictions
            if backup_scope == "full_system":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admins can import full system backups",
                )

            if backup_tenant_id and backup_tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot import backup from a different tenant",
                )

            # Import as-is; session tenant filtering will scope new data
            stats = BackupService.import_database(db, backup_data, clear_existing)

        # Return stats
        return {
            "success": len(stats["errors"]) == 0,
            "message": "Import completed successfully"
            if len(stats["errors"]) == 0
            else "Import completed with errors",
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import database: {str(e)}",
        )


@router.post("/validate", summary="Validate backup file")
async def validate_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Validate a backup file without importing it.

    Checks if the file is a valid backup and returns summary information.
    """
    try:
        # Read and parse the uploaded file
        contents = await file.read()

        try:
            backup_data = json.loads(contents)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON file: {str(e)}"
            )

        # Validate backup data
        is_valid, errors = BackupService.validate_backup(backup_data)

        if not is_valid:
            return {
                'valid': False,
                'errors': errors
            }

        # Get summary
        summary = BackupService.get_backup_summary(backup_data)

        return {
            'valid': True,
            'summary': summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate backup file: {str(e)}"
        )


@router.get("/summary", summary="Get current database summary")
async def get_database_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get summary of current database state.

    - Super admins: Summary for entire database
    - Regular users: Summary scoped to their tenant
    """
    try:
        # Super admins should see all tenants' data in summary
        skip_tenant_filter = current_user.is_super_admin
        backup_data = BackupService.export_database(db, skip_tenant_filter=skip_tenant_filter)
        summary = BackupService.get_backup_summary(backup_data)

        if current_user.is_super_admin:
            summary["scope"] = "full_system"
        else:
            summary["scope"] = "tenant"
            summary["tenant_id"] = current_user.tenant_id

        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database summary: {str(e)}",
        )


@router.get(
    "/export-archive", summary="Export full backup archive (database + files)"
)
async def export_backup_archive(
    include_files: bool = True,
    current_user: User = Depends(get_current_super_admin),  # Super admin only
) -> FileResponse:
    """
    Export a full backup archive including:
    - Complete database (ALL tenants)
    - Uploaded files (photos, documents, etc.) when include_files=True

    SUPER ADMIN ONLY.
    """
    from pathlib import Path
    import tempfile

    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tmp_dir = Path(tempfile.gettempdir())
        archive_path = tmp_dir / f"dcms_backup_{timestamp}.tar.gz"

        stats = create_backup_archive(archive_path, include_files=include_files, native=True)

        if stats.get("errors"):
            if archive_path.exists():
                archive_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create backup archive: {', '.join(stats['errors'])}",
            )

        if not archive_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Backup archive was not created.",
            )

        return FileResponse(
            path=str(archive_path),
            media_type="application/gzip",
            filename=archive_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export backup archive: {str(e)}",
        )


@router.post(
    "/import-archive", summary="Import full backup archive (database + files)"
)
async def import_backup_archive(
    file: UploadFile = File(...),
    clear_existing: bool = False,
    skip_files: bool = False,
    current_user: User = Depends(get_current_super_admin),  # Super admin only
) -> Dict[str, Any]:
    """
    Import a full backup archive created by the backup CLI or this API.

    SUPER ADMIN ONLY.
    """
    from pathlib import Path
    import tempfile
    import os

    try:
        tmp_dir = Path(tempfile.gettempdir())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_path = tmp_dir / f"dcms_restore_{timestamp}.tar.gz"

        contents = await file.read()
        with open(archive_path, "wb") as f:
            f.write(contents)

        result = restore_from_archive(
            archive_path,
            clear_existing=clear_existing,
            skip_files=skip_files,
        )

        if archive_path.exists():
            try:
                os.remove(archive_path)
            except OSError:
                pass

        if not result.get("success"):
            errors = result.get("errors", [])
            raise HTTPException(
                status_code=500,
                detail="Failed to import backup archive: "
                + (", ".join(errors) if errors else "Unknown error"),
            )

        return {
            "success": True,
            "message": "Archive import completed successfully",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import backup archive: {str(e)}",
        )

from app.services.native_backup_service import NativeBackupService

@router.get("/native/export", summary="Export full system native backup (pg_dump)")
async def export_native_backup(
    current_user: User = Depends(get_current_super_admin),
) -> FileResponse:
    """
    Export a full system native PostgreSQL dump.
    
    SUPER ADMIN ONLY.
    This creates a binary dump using pg_dump which preserves ALL schema, 
    relationships, sequences, and IDs exactly.
    """
    import tempfile
    from pathlib import Path
    
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tmp_dir = Path(tempfile.gettempdir())
        dump_path = tmp_dir / f"dcms_native_{timestamp}.dump"
        
        result = NativeBackupService.create_dump(dump_path)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create native backup: {result.get('error')}"
            )
            
        return FileResponse(
            path=str(dump_path),
            media_type="application/octet-stream",
            filename=dump_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export native backup: {str(e)}"
        )


@router.post("/native/import", summary="Restore full system native backup (pg_restore)")
async def import_native_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_super_admin),
) -> Dict[str, Any]:
    """
    Restore a full system native PostgreSQL dump.
    
    SUPER ADMIN ONLY.
    WARNING: This will DROP and RECREATE the entire database!
    All existing data will be lost and replaced with the backup content.
    """
    import tempfile
    from pathlib import Path
    import os
    
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tmp_dir = Path(tempfile.gettempdir())
        dump_path = tmp_dir / f"dcms_native_restore_{timestamp}.dump"
        
        # Save uploaded file
        contents = await file.read()
        with open(dump_path, "wb") as f:
            f.write(contents)
            
        # Perform restore
        result = NativeBackupService.restore_dump(dump_path, clean=True)
        
        # Clean up temp file
        if dump_path.exists():
            try:
                os.remove(dump_path)
            except OSError:
                pass
                
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restore native backup: {result.get('error')}"
            )
            
        return {
            "success": True,
            "message": "Native restore completed successfully",
            "warnings": result.get("warnings")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import native backup: {str(e)}"
        )
