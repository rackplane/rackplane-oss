# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Storage Service
Handles file storage in MinIO object storage

This service provides a unified interface for storing and retrieving files
(photos, documents) using MinIO. Falls back to local filesystem if MinIO
is not available.

Key Features:
- Upload files to MinIO buckets
- Generate presigned URLs for secure access
- Automatic bucket creation
- Fallback to local filesystem
- Tenant-scoped storage paths
"""

import os
import logging
from typing import Optional, BinaryIO
from datetime import timedelta
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import MinIO client
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    logger.warning("MinIO client not installed. Photo storage will use local filesystem.")


class StorageService:
    """
    Storage service for handling file uploads to MinIO or local filesystem.
    
    Provides a unified interface for storing photos and documents.
    """
    
    def __init__(self):
        """Initialize storage service with MinIO client if available."""
        self.minio_client: Optional[Minio] = None
        self.use_minio = False
        
        if MINIO_AVAILABLE:
            try:
                self.minio_client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                
                # Test connection and create bucket if needed
                self._ensure_bucket_exists()
                self.use_minio = True
                logger.info(f"MinIO storage initialized: {settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}")
            except Exception as e:
                logger.warning(f"Failed to initialize MinIO: {e}. Falling back to local filesystem.")
                self.minio_client = None
                self.use_minio = False
        else:
            logger.info("MinIO not available, using local filesystem storage")
    
    def _ensure_bucket_exists(self):
        """Ensure the default bucket exists in MinIO."""
        if not self.minio_client:
            return
        
        try:
            if not self.minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
                logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET_NAME}")
        except S3Error as e:
            logger.error(f"Failed to create MinIO bucket: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize storage bucket: {str(e)}"
            )
    
    def upload_file(
        self,
        file_data: bytes,
        file_path: str,
        content_type: str = "application/octet-stream",
        tenant_id: Optional[int] = None
    ) -> str:
        """
        Upload a file to storage (MinIO or local filesystem).
        
        Args:
            file_data: File content as bytes
            file_path: Path/filename for the file (e.g., "assets/photo_123.jpg")
            content_type: MIME type of the file
            tenant_id: Optional tenant ID for tenant-scoped storage
            
        Returns:
            Storage URL or path to the file
            
        Raises:
            HTTPException if upload fails
        """
        # Add tenant prefix if provided
        if tenant_id:
            file_path = f"tenant_{tenant_id}/{file_path}"
        
        if self.use_minio and self.minio_client:
            return self._upload_to_minio(file_data, file_path, content_type)
        else:
            return self._upload_to_local(file_data, file_path)
    
    def _upload_to_minio(
        self,
        file_data: bytes,
        file_path: str,
        content_type: str
    ) -> str:
        """Upload file to MinIO."""
        try:
            from io import BytesIO
            
            file_stream = BytesIO(file_data)
            file_size = len(file_data)
            
            self.minio_client.put_object(
                settings.MINIO_BUCKET_NAME,
                file_path,
                file_stream,
                file_size,
                content_type=content_type
            )
            
            # Return MinIO object path (can be converted to presigned URL later)
            url = f"minio://{settings.MINIO_BUCKET_NAME}/{file_path}"
            logger.info(f"Uploaded to MinIO: {url}")
            return url
            
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to storage: {str(e)}"
            )
    
    def _upload_to_local(
        self,
        file_data: bytes,
        file_path: str
    ) -> str:
        """Upload file to local filesystem."""
        try:
            # Ensure upload directory exists
            upload_dir = os.path.join(settings.UPLOAD_DIR, os.path.dirname(file_path))
            os.makedirs(upload_dir, exist_ok=True)
            
            # Write file
            full_path = os.path.join(settings.UPLOAD_DIR, file_path)
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            # Return relative path
            url = f"/uploads/{file_path}"
            logger.info(f"Uploaded to local storage: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    def get_presigned_url(
        self,
        file_path: str,
        expires: timedelta = timedelta(hours=1),
        tenant_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get a presigned URL for accessing a file.
        
        Args:
            file_path: Path to the file (MinIO object key or local path)
            expires: How long the URL should be valid
            tenant_id: Optional tenant ID for tenant-scoped paths
            
        Returns:
            Presigned URL or None if not using MinIO
        """
        if not self.use_minio or not self.minio_client:
            # For local files, return the path directly (served by FastAPI static files)
            if tenant_id:
                file_path = f"tenant_{tenant_id}/{file_path}"
            return f"/uploads/{file_path}"
        
        try:
            # Extract object key from minio:// URL if present
            if file_path.startswith("minio://"):
                # Format: minio://bucket/path
                parts = file_path.replace("minio://", "").split("/", 1)
                if len(parts) == 2:
                    bucket = parts[0]
                    object_key = parts[1]
                else:
                    object_key = file_path.replace("minio://", "")
                    bucket = settings.MINIO_BUCKET_NAME
            else:
                # Add tenant prefix if provided
                if tenant_id:
                    object_key = f"tenant_{tenant_id}/{file_path}"
                else:
                    object_key = file_path
                bucket = settings.MINIO_BUCKET_NAME
            
            url = self.minio_client.presigned_get_object(
                bucket,
                object_key,
                expires=expires
            )
            return url
            
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def delete_file(
        self,
        file_path: str,
        tenant_id: Optional[int] = None
    ) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file
            tenant_id: Optional tenant ID for tenant-scoped paths
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if self.use_minio and self.minio_client:
            return self._delete_from_minio(file_path, tenant_id)
        else:
            return self._delete_from_local(file_path, tenant_id)
    
    def _delete_from_minio(
        self,
        file_path: str,
        tenant_id: Optional[int]
    ) -> bool:
        """Delete file from MinIO."""
        try:
            # Extract object key from minio:// URL if present
            if file_path.startswith("minio://"):
                parts = file_path.replace("minio://", "").split("/", 1)
                if len(parts) == 2:
                    bucket = parts[0]
                    object_key = parts[1]
                else:
                    object_key = file_path.replace("minio://", "")
                    bucket = settings.MINIO_BUCKET_NAME
            else:
                if tenant_id:
                    object_key = f"tenant_{tenant_id}/{file_path}"
                else:
                    object_key = file_path
                bucket = settings.MINIO_BUCKET_NAME
            
            self.minio_client.remove_object(bucket, object_key)
            logger.info(f"Deleted from MinIO: {file_path}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete from MinIO: {e}")
            return False
    
    def _delete_from_local(
        self,
        file_path: str,
        tenant_id: Optional[int]
    ) -> bool:
        """Delete file from local filesystem."""
        try:
            if tenant_id:
                file_path = f"tenant_{tenant_id}/{file_path}"
            
            full_path = os.path.join(settings.UPLOAD_DIR, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted from local storage: {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete from local storage: {e}")
            return False
    
    def file_exists(
        self,
        file_path: str,
        tenant_id: Optional[int] = None
    ) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Path to the file
            tenant_id: Optional tenant ID for tenant-scoped paths
            
        Returns:
            True if file exists, False otherwise
        """
        if self.use_minio and self.minio_client:
            try:
                # Extract object key from minio:// URL if present
                if file_path.startswith("minio://"):
                    parts = file_path.replace("minio://", "").split("/", 1)
                    if len(parts) == 2:
                        bucket = parts[0]
                        object_key = parts[1]
                    else:
                        object_key = file_path.replace("minio://", "")
                        bucket = settings.MINIO_BUCKET_NAME
                else:
                    if tenant_id:
                        object_key = f"tenant_{tenant_id}/{file_path}"
                    else:
                        object_key = file_path
                    bucket = settings.MINIO_BUCKET_NAME
                
                self.minio_client.stat_object(bucket, object_key)
                return True
            except S3Error:
                return False
        else:
            if tenant_id:
                file_path = f"tenant_{tenant_id}/{file_path}"
            full_path = os.path.join(settings.UPLOAD_DIR, file_path)
            return os.path.exists(full_path)


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service

