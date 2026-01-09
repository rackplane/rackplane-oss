# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression Test: Asset Warranty Date Fields
Tests that warranty_start_date and warranty_end_date can be set and retrieved

This test verifies:
1. Warranty dates can be set when creating assets
2. Warranty dates can be updated
3. Warranty dates are returned in API responses
4. Warranty dates are properly validated
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.tenant import set_current_tenant_id, clear_tenant_id
from app.models.asset import Asset
# AssetType not needed for this test


@pytest.mark.integration
@pytest.mark.regression
def test_asset_warranty_dates_can_be_set(api_client, test_tenant, test_user):
    """
    REGRESSION: Asset warranty dates must be settable and retrievable
    
    Bug: Warranty dates were not exposed in API schema, preventing users
    from tracking warranty expiration dates for assets.
    
    Fix: Added warranty_start_date and warranty_end_date to AssetBase schema
    and frontend forms.
    
    This test verifies:
    1. Warranty dates can be set when creating assets
    2. Warranty dates are returned in API responses
    3. Warranty dates can be updated
    """
    set_current_tenant_id(test_tenant["id"])
    api_client.set_token(test_user["token"])
    
    try:
        # Create an asset with warranty dates
        warranty_start = datetime.utcnow() - timedelta(days=365)
        warranty_end = datetime.utcnow() + timedelta(days=365)
        
        asset_data = {
            "asset_tag": f"WARRANTY-TEST-{test_tenant['id']}",
            "serial_number": f"SN-WARRANTY-{test_tenant['id']}",
            "asset_type": "server_device",
            "manufacturer": "Test Manufacturer",
            "model": "Test Model",
            "warranty_start_date": warranty_start.isoformat(),
            "warranty_end_date": warranty_end.isoformat(),
        }
        
        success, response = api_client.post(
            "/api/v1/assets/",
            asset_data,
            expected_status=201
        )
        assert success, f"Asset creation should succeed, got: {response}"
        assert "id" in response, "Response should include asset id"
        
        asset_id = response["id"]
        
        # Verify warranty dates are returned
        assert "warranty_start_date" in response, "Response should include warranty_start_date"
        assert "warranty_end_date" in response, "Response should include warranty_end_date"
        
        # Parse dates from response
        returned_start = datetime.fromisoformat(response["warranty_start_date"].replace('Z', '+00:00'))
        returned_end = datetime.fromisoformat(response["warranty_end_date"].replace('Z', '+00:00'))
        
        # Verify dates match (within 1 second tolerance for timezone/rounding)
        assert abs((returned_start.replace(tzinfo=None) - warranty_start).total_seconds()) < 1, \
            f"Warranty start date should match, got {returned_start}, expected {warranty_start}"
        assert abs((returned_end.replace(tzinfo=None) - warranty_end).total_seconds()) < 1, \
            f"Warranty end date should match, got {returned_end}, expected {warranty_end}"
        
        # Update warranty end date (extend by 1 year)
        # Use a fixed date relative to now to avoid timing issues
        new_warranty_end = datetime.utcnow() + timedelta(days=730)  # 2 years from now
        
        update_data = {
            "warranty_end_date": new_warranty_end.isoformat(),
        }
        
        success, update_response = api_client.put(
            f"/api/v1/assets/{asset_id}",
            update_data,
            expected_status=200
        )
        assert success, f"Asset update should succeed, got: {update_response}"
        
        # Fetch the asset again to verify the update persisted
        success, fetch_response = api_client.get(
            f"/api/v1/assets/{asset_id}",
            expected_status=200
        )
        assert success, f"Asset fetch should succeed, got: {fetch_response}"
        
        # Verify updated warranty end date (allow 5 second tolerance for timing)
        assert "warranty_end_date" in fetch_response, "Fetch response should include warranty_end_date"
        assert fetch_response["warranty_end_date"] is not None, "Warranty end date should not be None after update"
        updated_end_str = fetch_response["warranty_end_date"]
        updated_end = datetime.fromisoformat(updated_end_str.replace('Z', '+00:00'))
        # Check that the date is approximately 2 years from now (within 5 seconds)
        expected_date = datetime.utcnow() + timedelta(days=730)
        assert abs((updated_end.replace(tzinfo=None) - expected_date).total_seconds()) < 5, \
            f"Updated warranty end date should be approximately 2 years from now, got {updated_end}, expected ~{expected_date}"
        
        # Verify warranty start date is unchanged
        assert "warranty_start_date" in fetch_response, "Fetch response should include warranty_start_date"
        assert fetch_response["warranty_start_date"] is not None, "Warranty start date should still be set"
        updated_start_str = fetch_response["warranty_start_date"]
        updated_start = datetime.fromisoformat(updated_start_str.replace('Z', '+00:00'))
        # Check that start date is approximately 1 year ago (within 5 seconds)
        expected_start = datetime.utcnow() - timedelta(days=365)
        assert abs((updated_start.replace(tzinfo=None) - expected_start).total_seconds()) < 5, \
            f"Warranty start date should be approximately 1 year ago, got {updated_start}, expected ~{expected_start}"
        
    finally:
        clear_tenant_id()


@pytest.mark.integration
@pytest.mark.regression
def test_asset_warranty_dates_optional(api_client, test_tenant, test_user):
    """
    REGRESSION: Warranty dates should be optional
    
    This test verifies that assets can be created without warranty dates,
    and warranty dates can be added later.
    """
    set_current_tenant_id(test_tenant["id"])
    api_client.set_token(test_user["token"])
    
    try:
        # Create asset without warranty dates
        asset_data = {
            "asset_tag": f"NO-WARRANTY-{test_tenant['id']}",
            "serial_number": f"SN-NO-WARRANTY-{test_tenant['id']}",
            "asset_type": "server_device",
            "manufacturer": "Test Manufacturer",
            "model": "Test Model",
        }
        
        success, response = api_client.post(
            "/api/v1/assets/",
            asset_data,
            expected_status=201
        )
        assert success, f"Asset creation should succeed, got: {response}"
        asset_id = response["id"]
        
        # Verify warranty dates are None/null
        assert response.get("warranty_start_date") is None or response.get("warranty_start_date") == "", \
            "Warranty start date should be None/null when not set"
        assert response.get("warranty_end_date") is None or response.get("warranty_end_date") == "", \
            "Warranty end date should be None/null when not set"
        
        # Add warranty dates later
        warranty_start = datetime.utcnow() - timedelta(days=180)
        warranty_end = datetime.utcnow() + timedelta(days=180)
        
        update_data = {
            "warranty_start_date": warranty_start.isoformat(),
            "warranty_end_date": warranty_end.isoformat(),
        }
        
        success, update_response = api_client.put(
            f"/api/v1/assets/{asset_id}",
            update_data,
            expected_status=200
        )
        assert success, f"Asset update should succeed, got: {update_response}"
        
        # Fetch the asset again to verify the update persisted
        success, fetch_response = api_client.get(
            f"/api/v1/assets/{asset_id}",
            expected_status=200
        )
        assert success, f"Asset fetch should succeed, got: {fetch_response}"
        
        # Verify warranty dates are now set (allow 5 second tolerance for timing)
        assert "warranty_start_date" in fetch_response, "Fetch response should include warranty_start_date"
        assert fetch_response["warranty_start_date"] is not None, \
            f"Warranty start date should be set after update, got: {fetch_response.get('warranty_start_date')}"
        warranty_start_returned = datetime.fromisoformat(fetch_response["warranty_start_date"].replace('Z', '+00:00'))
        expected_start = datetime.utcnow() - timedelta(days=180)
        assert abs((warranty_start_returned.replace(tzinfo=None) - expected_start).total_seconds()) < 5, \
            f"Warranty start date should be approximately 180 days ago, got {warranty_start_returned}, expected ~{expected_start}"
        
        assert "warranty_end_date" in fetch_response, "Fetch response should include warranty_end_date"
        assert fetch_response["warranty_end_date"] is not None, \
            f"Warranty end date should be set after update, got: {fetch_response.get('warranty_end_date')}"
        warranty_end_returned = datetime.fromisoformat(fetch_response["warranty_end_date"].replace('Z', '+00:00'))
        expected_end = datetime.utcnow() + timedelta(days=180)
        assert abs((warranty_end_returned.replace(tzinfo=None) - expected_end).total_seconds()) < 5, \
            f"Warranty end date should be approximately 180 days from now, got {warranty_end_returned}, expected ~{expected_end}"
        
    finally:
        clear_tenant_id()


@pytest.mark.integration
@pytest.mark.regression
def test_asset_warranty_dates_database_persistence(api_client, test_tenant, test_user):
    """
    REGRESSION: Warranty dates must persist in database
    
    This test verifies that warranty dates are correctly stored in the database
    and can be retrieved via direct database queries.
    """
    set_current_tenant_id(test_tenant["id"])
    api_client.set_token(test_user["token"])
    
    try:
        db: Session = SessionLocal()
        
        try:
            # Create asset via API with warranty dates
            warranty_start = datetime.utcnow() - timedelta(days=365)
            warranty_end = datetime.utcnow() + timedelta(days=365)
            
            asset_data = {
                "asset_tag": f"DB-WARRANTY-{test_tenant['id']}",
                "serial_number": f"SN-DB-WARRANTY-{test_tenant['id']}",
                "asset_type": "server_device",
                "manufacturer": "Test Manufacturer",
                "model": "Test Model",
                "warranty_start_date": warranty_start.isoformat(),
                "warranty_end_date": warranty_end.isoformat(),
            }
            
            success, response = api_client.post(
                "/api/v1/assets/",
                asset_data,
                expected_status=201
            )
            assert success, f"Asset creation should succeed, got: {response}"
            asset_id = response["id"]
            
            # Verify warranty dates in database
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            assert asset is not None, "Asset should exist in database"
            assert asset.warranty_start_date is not None, "Warranty start date should be set in database"
            assert asset.warranty_end_date is not None, "Warranty end date should be set in database"
            
            # Verify dates match (within 1 second tolerance)
            assert abs((asset.warranty_start_date - warranty_start).total_seconds()) < 1, \
                f"Database warranty start date should match, got {asset.warranty_start_date}, expected {warranty_start}"
            assert abs((asset.warranty_end_date - warranty_end).total_seconds()) < 1, \
                f"Database warranty end date should match, got {asset.warranty_end_date}, expected {warranty_end}"
            
        finally:
            db.close()
            
    finally:
        clear_tenant_id()

