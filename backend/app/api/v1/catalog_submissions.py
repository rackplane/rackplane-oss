# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog Submissions API
Endpoints for submitting, reviewing, and approving catalog contributions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update, func, tuple_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.auth import get_current_active_user, get_current_tenant_admin
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.models.api_customer import ApiCustomer
from app.models.catalog_submission import CatalogSubmission
from app.models.catalog_sku import CatalogSKU
from app.models.user_role import UserRole
from app.services.catalog_sync_service import CatalogSyncService
from app.utils.audit_helpers import audit_create, audit_update, audit_delete
from app.services.audit_service import get_model_dict

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Status constants
STATUS_PENDING = "pending"
STATUS_TENANT_APPROVED = "tenant_approved"  # Approved by Tenant Admin, awaiting Super Admin
STATUS_APPROVED = "approved"  # Approved by Super Admin, added to global catalog
STATUS_REJECTED = "rejected"


# Helper functions for sync_info structure
def create_sync_success_info(source_id: str) -> dict:
    """Create a sync_info dict for successful syncs."""
    return {
        "status": "success",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id
    }


def create_sync_failure_info(error_msg: str) -> dict:
    """Create a sync_info dict for failed syncs."""
    return {
        "status": "failed",
        "error": error_msg,
        "failed_at": datetime.now(timezone.utc).isoformat()
    }


# Pydantic models
class SubmissionData(BaseModel):
    """Data for a catalog submission."""
    vendor: str
    sku: str
    name: str
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    asset_type: Optional[str] = None
    description: Optional[str] = None
    price_usd: Optional[float] = None
    currency: Optional[str] = "USD"
    specifications: Optional[dict] = None
    datasheet_url: Optional[str] = None
    vendor_url: Optional[str] = None
    image_url: Optional[str] = None


class SubmissionCreate(BaseModel):
    """Request to create a submission."""
    data: SubmissionData
    source_url: Optional[str] = None
    submission_method: Optional[str] = "manual_edit"


class ScrapeRequest(BaseModel):
    """Request to scrape a URL."""
    url: str


class ReviewRequest(BaseModel):
    """Request to approve/reject a submission."""
    notes: Optional[str] = None


class SubmissionResponse(BaseModel):
    """Response for a submission."""
    id: int
    vendor: str
    sku: str
    data_snapshot: dict
    source_url: Optional[str]
    submission_method: str
    status: str
    submitted_by_user_id: int
    submitted_at: datetime
    reviewed_by_user_id: Optional[int]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    
    class Config:
        from_attributes = True


def is_admin_or_tenant_admin(user: User) -> bool:
    """Check if user has admin or tenant admin permissions.
    
    Uses both effective_role AND is_super_admin flag for safety,
    ensuring we catch super admins regardless of which field is set.
    
    NOTE: This helper is primarily for delete_submission where we need
    to check permissions without requiring the get_current_tenant_admin dependency.
    For other admin endpoints, prefer using Depends(get_current_tenant_admin).
    """
    return (
        user.is_super_admin or 
        user.effective_role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]
    )


def is_super_admin(user: User) -> bool:
    """Check if user is a super admin using both fields for safety."""
    return user.is_super_admin or user.effective_role == UserRole.SUPER_ADMIN


def get_allowed_statuses_for_review(user: User) -> list:
    """Get the list of statuses a user can act on (approve/reject).
    
    Super Admins can act on both pending and tenant_approved submissions.
    Tenant Admins can only act on pending submissions.
    
    Returns:
        List of status strings the user is allowed to review.
    """
    if is_super_admin(user):
        return [STATUS_PENDING, STATUS_TENANT_APPROVED]
    return [STATUS_PENDING]


def validate_submission_status_for_review(submission: CatalogSubmission, user: User) -> None:
    """Validate that a submission is in a status the user can act on.
    
    Raises:
        HTTPException: If submission status is not actionable by this user.
    """
    allowed_statuses = get_allowed_statuses_for_review(user)
    if submission.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Submission is already {submission.status}")


@router.post("/", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    submission: SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit SKU data for inclusion in the global catalog.
    
    Any authenticated user can submit. Submissions go to a review queue
    where admins can approve or reject them.
    """
    # Check if already submitted (pending)
    existing = db.query(CatalogSubmission).filter(
        CatalogSubmission.vendor == submission.data.vendor,
        CatalogSubmission.sku == submission.data.sku,
        CatalogSubmission.status == STATUS_PENDING
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A pending submission for {submission.data.vendor} {submission.data.sku} already exists"
        )
    
    # Check if exists in catalog already
    existing_catalog = db.query(CatalogSKU).filter(
        CatalogSKU.vendor == submission.data.vendor,
        CatalogSKU.sku == submission.data.sku
    ).first()
    
    # Create submission
    catalog_submission = CatalogSubmission(
        vendor=submission.data.vendor,
        sku=submission.data.sku,
        data_snapshot=submission.data.dict(),
        source_url=submission.source_url,
        submission_method=submission.submission_method or "manual_edit",
        existing_catalog_sku_id=existing_catalog.id if existing_catalog else None,
        submitted_by_user_id=current_user.id,
        submitted_at=datetime.now(timezone.utc),
        status=STATUS_PENDING
    )
    
    db.add(catalog_submission)
    db.commit()
    db.refresh(catalog_submission)
    
    audit_create(db, catalog_submission, current_user, request)
    
    return catalog_submission


@router.post("/scrape", response_model=dict)
async def scrape_url(
    request: ScrapeRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Scrape product data from a URL.
    
    Returns extracted product data that can be edited before submission.
    Supports Amazon and generic vendor pages.
    """
    try:
        data = await BrowserScraperService.scrape_url(request.url)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parse-html", response_model=dict)
async def parse_html(
    html: str = Body(..., embed=True),
    vendor: str = Body("Unknown"),
    url: str = Body(""),
    current_user: User = Depends(get_current_active_user)
):
    """
    Parse HTML content directly (for bookmarklet use).
    
    Bookmarklet sends the page HTML, this endpoint parses it.
    """
    try:
        data = BrowserScraperService.parse_html(html, vendor=vendor, url=url)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SubmissionResponse])
async def list_submissions(
    status: Optional[str] = Query(None, description="Filter by status (pending/tenant_approved/approved/rejected)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List catalog submissions.
    
    Super Admins see all submissions across all tenants.
    Tenant Admins see all submissions in their tenant.
    Regular users only see their own submissions.
    """
    # Use joinedload to prevent N+1 queries when accessing submitted_by
    query = (
        db.query(CatalogSubmission)
        .options(joinedload(CatalogSubmission.submitted_by))
    )
    
    # Permission-based filtering using .has() for relationship filters
    if is_super_admin(current_user):
        # Super Admins see all - no filter needed
        pass
    elif current_user.effective_role == UserRole.TENANT_ADMIN:
        # Tenant Admins see all submissions in their tenant
        query = query.filter(
            CatalogSubmission.submitted_by.has(tenant_id=current_user.tenant_id)
        )
    else:
        # Regular users only see their own
        query = query.filter(CatalogSubmission.submitted_by_user_id == current_user.id)
    
    if status:
        query = query.filter(CatalogSubmission.status == status)
    
    if vendor:
        query = query.filter(CatalogSubmission.vendor.ilike(f"%{vendor}%"))
    
    return query.order_by(CatalogSubmission.submitted_at.desc()).limit(limit).all()


@router.get("/pending", response_model=List[SubmissionResponse])
async def list_pending_submissions(
    vendor: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    List pending submissions (admin only).
    """
    # Use joinedload to prevent N+1 queries when accessing submitted_by.tenant_id
    query = (
        db.query(CatalogSubmission)
        .options(joinedload(CatalogSubmission.submitted_by))
        .filter(CatalogSubmission.status == STATUS_PENDING)
    )
    
    # Tenant Admin boundary check: only see submissions from their own tenant.
    # Use the relationship in the filter to avoid combining joinedload with an explicit join.
    if current_user.effective_role != UserRole.SUPER_ADMIN and not current_user.is_super_admin:
        query = query.filter(
            CatalogSubmission.submitted_by.has(
                tenant_id=current_user.tenant_id
            )
        )
    
    if vendor:
        query = query.filter(CatalogSubmission.vendor.ilike(f"%{vendor}%"))
    
    return query.order_by(CatalogSubmission.submitted_at.asc()).limit(limit).all()


@router.get("/my-submissions", response_model=List[SubmissionResponse])
async def list_my_submissions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List current user's submissions.
    """
    # Use joinedload to prevent N+1 queries for consistency with other list endpoints
    query = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.submitted_by_user_id == current_user.id
    )
    
    if status:
        query = query.filter(CatalogSubmission.status == status)
    
    return query.order_by(CatalogSubmission.submitted_at.desc()).limit(limit).all()


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific submission.
    """
    submission = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Permission check - users can only view their own submissions
    if not is_admin_or_tenant_admin(current_user) and submission.submitted_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Tenant boundary check for tenant admins - they can only view submissions from their tenant
    if not is_super_admin(current_user) and is_admin_or_tenant_admin(current_user):
        if not submission.submitted_by or submission.submitted_by.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return submission


@router.put("/{submission_id}/approve", response_model=SubmissionResponse)
async def approve_submission(
    submission_id: int,
    request: Request,
    review: ReviewRequest = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Approve a submission.
    
    Two-stage workflow:
    - Tenant Admin: Approves pending -> tenant_approved (local approval only)
    - Super Admin: Approves pending OR tenant_approved -> approved (adds to global catalog)
    """
    submission = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Tenant boundary check for non-super-admins
    # Use generic error message to avoid information disclosure
    if not is_super_admin(current_user):
        if not submission.submitted_by or submission.submitted_by.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate status is actionable by this user
    validate_submission_status_for_review(submission, current_user)
    user_is_super = is_super_admin(current_user)
    
    # Audit preparation
    old_values = get_model_dict(submission)
    
    if user_is_super:
        # SUPER ADMIN: Final approval - add to global catalog
        data = submission.data_snapshot
        
        catalog_sku = db.query(CatalogSKU).filter(
            CatalogSKU.vendor == submission.vendor,
            CatalogSKU.sku == submission.sku
        ).first()
        
        if catalog_sku:
            # Capture old values BEFORE mutation for accurate audit trail
            catalog_sku_old_values = get_model_dict(catalog_sku)
            
            # Update existing
            catalog_sku.name = data.get("name", catalog_sku.name)
            catalog_sku.manufacturer = data.get("manufacturer", catalog_sku.manufacturer)
            catalog_sku.part_number = data.get("part_number", catalog_sku.part_number)
            catalog_sku.asset_type = data.get("asset_type", catalog_sku.asset_type)
            catalog_sku.description = data.get("description", catalog_sku.description)
            catalog_sku.price_usd = data.get("price_usd", catalog_sku.price_usd)
            catalog_sku.currency = data.get("currency", catalog_sku.currency)
            catalog_sku.specifications = data.get("specifications", catalog_sku.specifications)
            catalog_sku.datasheet_url = data.get("datasheet_url", catalog_sku.datasheet_url)
            catalog_sku.vendor_url = data.get("vendor_url", catalog_sku.vendor_url)
            catalog_sku.updated_at = datetime.now(timezone.utc)
            db.flush()
            audit_update(db, catalog_sku, current_user, request, old_values=catalog_sku_old_values)
        else:
            # Create new
            catalog_sku = CatalogSKU(
                vendor=submission.vendor,
                sku=submission.sku,
                name=data.get("name", ""),
                manufacturer=data.get("manufacturer"),
                part_number=data.get("part_number"),
                asset_type=data.get("asset_type"),
                description=data.get("description"),
                price_usd=data.get("price_usd"),
                currency=data.get("currency", "USD"),
                specifications=data.get("specifications"),
                datasheet_url=data.get("datasheet_url"),
                vendor_url=data.get("vendor_url") or submission.source_url,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(catalog_sku)
            db.flush()
            audit_create(db, catalog_sku, current_user, request)
        
        # Final approved status
        submission.status = STATUS_APPROVED
        submission.reviewed_by_user_id = current_user.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.review_notes = review.notes if review else None

        # Increment contribution credit for submitting tenant
        submitter = submission.submitted_by
        if submitter and submitter.tenant_id:
            # Use single query with JOIN for efficiency
            result = (
                db.query(Tenant.uuid, ApiCustomer.contributor_since)
                .outerjoin(ApiCustomer, ApiCustomer.tenant_id == Tenant.uuid)
                .filter(Tenant.id == submitter.tenant_id)
                .first()
            )

            if result and result[0]:  # result[0] is Tenant.uuid
                tenant_uuid = result[0]
                contributor_since = result[1]  # ApiCustomer.contributor_since or None

                # Atomically increment contribution count (prevents race conditions)
                # Use func.coalesce to preserve earliest contributor_since atomically
                stmt = update(ApiCustomer).where(
                    ApiCustomer.tenant_id == tenant_uuid
                ).values(
                    contribution_count=ApiCustomer.contribution_count + 1,
                    contributor_since=func.coalesce(ApiCustomer.contributor_since, datetime.now(timezone.utc)),
                    is_lifetime_contributor=True
                )
                result = db.execute(stmt)

                if result.rowcount > 0:
                    logger.info(f"Incremented contribution credit for tenant {tenant_uuid}")
                else:
                    # ApiCustomer doesn't exist - create it
                    # This can happen if tenant never provisioned API key
                    tenant = db.query(Tenant).filter(Tenant.id == submitter.tenant_id).first()
                    if tenant:
                        new_customer = ApiCustomer(
                            tenant_id=tenant_uuid,
                            api_key_hash="",  # Will be set when they provision
                            customer_name=tenant.name,
                            email=tenant.contact_email,
                            tier="community",
                            rate_limit_hour=50,
                            is_active=True,
                            contribution_count=1,
                            contributor_since=datetime.now(timezone.utc),
                            is_lifetime_contributor=True
                        )
                        db.add(new_customer)
                        logger.info(f"Created ApiCustomer for tenant {tenant_uuid} with first contribution")

        db.commit()
        db.refresh(submission)
        
        audit_update(db, submission, current_user, request, old_values)
        
        # Sync to Central Catalog in background (Super Admin only)
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        api_key = tenant.rackplane_api_key if tenant else None
        tenant_uuid = tenant.uuid if tenant else None

        background_tasks.add_task(
            sync_catalog_item_background,
            submission_id=submission.id,
            sku_id=catalog_sku.id,
            submission_data=data,
            vendor=submission.vendor,
            sku=submission.sku,
            api_key=api_key,
            sync_secret=settings.RACKPLANE_SYNC_SECRET,
            tenant_uuid=tenant_uuid
        )
    else:
        # TENANT ADMIN: First stage approval (no catalog write)
        submission.status = STATUS_TENANT_APPROVED
        submission.reviewed_by_user_id = current_user.id
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.review_notes = review.notes if review else None
        
        db.commit()
        db.refresh(submission)
        
        audit_update(db, submission, current_user, request, old_values)
    
    return submission


def sync_catalog_item_background(
    submission_id: int,
    sku_id: int,
    submission_data: dict,
    vendor: str,
    sku: str,
    api_key: str = None,
    sync_secret: str = None,
    tenant_uuid: str = None
):
    """Background task to sync catalog item to central server."""
    try:
        # Create a new DB session for the background task
        from app.core.database import SessionLocal
        from app.models.catalog_sku import CatalogSKU
        from app.models.catalog_submission import CatalogSubmission
        from sqlalchemy.orm.attributes import flag_modified
        
        db = SessionLocal()
        try:
            # Fetch submission with lock to prevent race conditions during status update
            submission = db.query(CatalogSubmission).filter(
                CatalogSubmission.id == submission_id
            ).with_for_update().first()

            if not submission:
                logger.error(f"Submission {submission_id} not found in background task")
                return

            # Ensure vendor/sku are in data snapshot if missing
            sync_data = submission_data.copy()
            if "vendor" not in sync_data:
                sync_data["vendor"] = vendor
            if "sku" not in sync_data:
                sync_data["sku"] = sku
            if tenant_uuid:
                sync_data["tenant_uuid"] = tenant_uuid

            source_id, error_msg = CatalogSyncService.push_to_central(
                sync_data,
                api_key=api_key,
                sync_secret=sync_secret
            )

            # Update submission with sync status info
            if not submission.data_snapshot:
                submission.data_snapshot = {}

            if source_id:
                submission.data_snapshot["sync_info"] = create_sync_success_info(source_id)
                # Re-fetch SKU to update it with lock
                catalog_sku = db.query(CatalogSKU).filter(
                    CatalogSKU.id == sku_id
                ).with_for_update().first()
                if catalog_sku:
                    catalog_sku.source_id = source_id
                    catalog_sku.last_synced_at = datetime.now(timezone.utc)
            else:
                submission.data_snapshot["sync_info"] = create_sync_failure_info(error_msg)

            flag_modified(submission, "data_snapshot")
            db.commit()
        except Exception as inner_error:
            logger.error(f"Error in background sync, rolling back: {inner_error}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        # Logged with full stack trace for easier debugging
        logger.exception(f"Fatal error in background sync for submission {submission_id}: {str(e)}")

        # Attempt to record failure in DB if possible
        db_err = None
        try:
            db_err = SessionLocal()
            sub = db_err.get(CatalogSubmission, submission_id)
            if sub:
                if not sub.data_snapshot: sub.data_snapshot = {}
                sub.data_snapshot["sync_info"] = create_sync_failure_info(f"System Error: {str(e)[:200]}")
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(sub, "data_snapshot")
                db_err.commit()
        except Exception as final_err:
            logger.exception(f"Failed to record sync failure for submission {submission_id}: {final_err}")
            if db_err:
                db_err.rollback()
        finally:
            if db_err:
                db_err.close()


@router.put("/{submission_id}/reject", response_model=SubmissionResponse)
async def reject_submission(
    submission_id: int,
    review: ReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Reject a submission.
    
    Admin only. Submission is marked as rejected with notes.
    """
    submission = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Tenant boundary check - use generic error message to avoid information disclosure
    if not is_super_admin(current_user):
        if not submission.submitted_by or submission.submitted_by.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate status is actionable by this user
    validate_submission_status_for_review(submission, current_user)
    
    # Audit preparation
    old_values = get_model_dict(submission)
    
    # Update submission status
    submission.status = STATUS_REJECTED
    submission.reviewed_by_user_id = current_user.id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.review_notes = review.notes
    
    db.commit()
    db.refresh(submission)
    
    audit_update(db, submission, current_user, request, old_values)
    
    return submission


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(
    submission_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a submission (only if pending and owned by user).
    """
    submission = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Permission check - users can only delete their own submissions
    if not is_admin_or_tenant_admin(current_user) and submission.submitted_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Tenant boundary check for tenant admins - they can only delete submissions from their tenant
    if not is_super_admin(current_user) and is_admin_or_tenant_admin(current_user):
        if not submission.submitted_by or submission.submitted_by.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    if submission.status != STATUS_PENDING and not is_admin_or_tenant_admin(current_user):
        raise HTTPException(status_code=400, detail="Cannot delete non-pending submission")
    
    audit_delete(db, submission, current_user, request)
    
    db.delete(submission)
    db.commit()
    
    return None


@router.post("/{submission_id}/resync", response_model=dict)
async def resync_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Re-sync an approved submission to the global catalog.
    
    Use this when:
    - Initial sync failed (check data_snapshot.sync_info.status)
    - You want to push updated data to the central catalog
    - The central catalog was reset and needs repopulating
    
    Super Admin only.
    """
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only Super Admins can resync to global catalog")
    
    submission = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by)
    ).filter(
        CatalogSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != STATUS_APPROVED:
        raise HTTPException(
            status_code=400, 
            detail=f"Only approved submissions can be resynced. Current status: {submission.status}"
        )
    
    # Find the associated CatalogSKU
    catalog_sku = db.query(CatalogSKU).filter(
        CatalogSKU.vendor == submission.vendor,
        CatalogSKU.sku == submission.sku
    ).first()
    
    if not catalog_sku:
        raise HTTPException(
            status_code=404, 
            detail=f"CatalogSKU for {submission.vendor}:{submission.sku} not found. Approve the submission first."
        )
    
    # Get API key from submission's tenant (not current user's tenant for cross-tenant resyncs)
    # This ensures the original submitter's credit is tracked correctly
    submitter = submission.submitted_by
    if not submitter:
        raise HTTPException(
            status_code=400,
            detail="Cannot resync: submission has no owner information"
        )
    submitter_tenant_id = submitter.tenant_id
    tenant = db.query(Tenant).filter(Tenant.id == submitter_tenant_id).first() if submitter_tenant_id else None
    # Only use API key if tenant exists and is active
    api_key = tenant.rackplane_api_key if (tenant and tenant.is_active) else None
    
    # Queue the sync
    background_tasks.add_task(
        sync_catalog_item_background,
        submission_id=submission.id,
        sku_id=catalog_sku.id,
        submission_data=submission.data_snapshot,
        vendor=submission.vendor,
        sku=submission.sku,
        api_key=api_key,
        sync_secret=settings.RACKPLANE_SYNC_SECRET
    )
    
    return {
        "message": f"Resync queued for {submission.vendor}:{submission.sku}",
        "submission_id": submission.id,
        "catalog_sku_id": catalog_sku.id,
        "previous_sync_info": submission.data_snapshot.get("sync_info") if submission.data_snapshot else None
    }


@router.post("/resync-all-failed", response_model=dict)
async def resync_all_failed(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Re-sync all approved submissions that have a failed sync status OR are missing sync information.
    
    Super Admin only. Useful for bulk recovery after central catalog issues.
    
    Returns:
        dict: {
            "message": str - Status message,
            "queued_count": int - Number of submissions queued for resync,
            "total_failed": int - Total number of failed submissions found
        }
    
    Raises:
        HTTPException: 403 if user is not a super admin
    """
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only Super Admins can resync to global catalog")
    
    # Find all approved submissions with failed sync
    # Find all approved submissions with failed sync
    # Use joinedload to prevent N+1 queries and ensure we have access to submitted_by.tenant for API keys
    submissions = db.query(CatalogSubmission).options(
        joinedload(CatalogSubmission.submitted_by).joinedload(User.tenant)
    ).filter(
        CatalogSubmission.status == STATUS_APPROVED
    ).all()
    
    failed_submissions = []
    for sub in submissions:
        sync_info = sub.data_snapshot.get("sync_info", {}) if sub.data_snapshot else {}
        if sync_info.get("status") == "failed" or not sync_info.get("status"):
            failed_submissions.append(sub)
    
    # Batch fetch all associated CatalogSKUs to avoid N+1 query
    if not failed_submissions:
        return {"message": "No failed submissions found to resync"}

    # specific (vendor, sku) pairs to look up
    sku_keys = [(sub.vendor, sub.sku) for sub in failed_submissions]
    
    # Use tuple_ for efficient multi-column IN clause
    catalog_skus = db.query(CatalogSKU).filter(
        tuple_(CatalogSKU.vendor, CatalogSKU.sku).in_(sku_keys)
    ).all()
    
    # Map (vendor, sku) -> CatalogSKU for O(1) lookup
    skus_map = {(sku.vendor, sku.sku): sku for sku in catalog_skus}
    
    queued_count = 0

    for submission in failed_submissions:
        # Lookup in map instead of DB
        catalog_sku = skus_map.get((submission.vendor, submission.sku))
        
        # Determine API Key: Use submitter's tenant key to ensure correct credit attribution
        submitter = submission.submitted_by
        
        # Skip submissions without an owner (consistent with single resync policy)
        if not submitter:
            continue
            
        submission_api_key = None
        if submitter.tenant and submitter.tenant.is_active:
            submission_api_key = submitter.tenant.rackplane_api_key
        
        if catalog_sku:
            background_tasks.add_task(
                sync_catalog_item_background,
                submission_id=submission.id,
                sku_id=catalog_sku.id,
                submission_data=submission.data_snapshot,
                vendor=submission.vendor,
                sku=submission.sku,
                api_key=submission_api_key,
                sync_secret=settings.RACKPLANE_SYNC_SECRET
            )
            queued_count += 1

    return {
        "message": f"Resync queued for {queued_count} failed submissions",
        "queued_count": queued_count,
        "total_failed": len(failed_submissions)
    }

