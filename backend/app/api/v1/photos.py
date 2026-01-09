# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Photo Serving Endpoints
Serve photos from MinIO or local storage
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
import base64
import io

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant import get_current_tenant_id
from app.models.user import User
from app.services.storage_service import get_storage_service

router = APIRouter()


@router.get("/serve")
async def serve_photo(
    url: str = Query(..., description="Photo URL (MinIO path or base64 data URL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Serve a photo from storage.
    
    Handles:
    - MinIO URLs: Returns presigned URL redirect or file stream
    - Base64 data URLs: Decodes and serves the image
    - Local paths: Serves from local filesystem
    
    Args:
        url: Photo URL from asset.photo_urls
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Image file stream or redirect to presigned URL
    """
    tenant_id = get_current_tenant_id()
    storage_service = get_storage_service()
    
    # Handle base64 data URLs (from backups)
    if url.startswith('data:image/'):
        try:
            # Extract base64 data
            # Format: data:image/jpeg;base64,/9j/4AAQSkZJRg...
            header, encoded = url.split(',', 1)
            content_type = header.split(';')[0].split(':')[1]  # Extract image/jpeg
            
            # Decode base64
            image_data = base64.b64decode(encoded)
            
            # Return as streaming response
            return StreamingResponse(
                io.BytesIO(image_data),
                media_type=content_type,
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 data URL: {str(e)}"
            )
    
    # Handle MinIO URLs
    if url.startswith('minio://'):
        # Get presigned URL from MinIO
        presigned_url = storage_service.get_presigned_url(
            file_path=url,
            expires=timedelta(hours=1),
            tenant_id=tenant_id
        )
        
        if presigned_url:
            # Redirect to presigned URL
            return RedirectResponse(url=presigned_url, status_code=302)
        else:
            raise HTTPException(
                status_code=404,
                detail="Photo not found in storage"
            )
    
    # Handle local paths (/uploads/...)
    if url.startswith('/uploads/'):
        # For local files, serve directly (FastAPI static files)
        # Or read from filesystem and stream
        from app.core.config import settings
        import os
        
        file_path = url.replace('/uploads/', '')
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)
        
        if tenant_id:
            # Check tenant-scoped path
            tenant_path = os.path.join(settings.UPLOAD_DIR, f"tenant_{tenant_id}", file_path)
            if os.path.exists(tenant_path):
                full_path = tenant_path
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Photo not found")
        
        # Determine content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(full_path)
        if not content_type:
            content_type = "image/jpeg"
        
        # Stream file
        def iterfile():
            with open(full_path, 'rb') as f:
                yield from f
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    # Unknown URL format
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported photo URL format: {url[:50]}..."
    )

