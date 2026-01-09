"""
Regression tests for SKU import error handling.

Bug: Import from Global Catalog showed "Failed to import: [object Object]" instead of actual error message
Fix: Added proper error message extraction in handleProductImport (VendorSKUs.tsx)
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.regression
@pytest.mark.integration  
class TestSKUImportErrorHandling:
    """
    REGRESSION: SKU import should return readable error messages, not [object Object]
    
    Bug: When API returns error.detail as an object like {error: "...", message: "..."},
         the frontend was displaying "[object Object]" instead of the actual message.
    Fix: VendorSKUs.tsx handleProductImport now properly extracts error messages from
         various response formats (string detail, object detail with message/error, etc.)
    """
    
    @pytest.mark.regression
    def test_vendor_sku_create_returns_string_error_on_duplicate(self, authenticated_client, test_prefix):
        """
        Verifies that duplicate SKU error returns a string message, not an object.
        This tests the backend side - the frontend fix handles the response formatting.
        """
        sku_data = {
            "vendor": "Test Vendor",
            "sku": f"{test_prefix}-DUP-SKU-001",
            "name": "Test Product for Duplicate Test"
        }
        
        # Create first SKU (should succeed if feature is enabled)
        success1, response1 = authenticated_client.post("/api/v1/vendor-skus/", sku_data, expected_status=201)
        
        if not success1:
            # Feature might be disabled - check for 402
            if isinstance(response1, dict) and response1.get("detail", {}).get("error") == "Premium feature not available":
                pytest.skip("SKU feature not enabled for this tenant")
            # Other error - fail test
            pytest.fail(f"Failed to create first SKU: {response1}")
        
        # Try to create duplicate (should fail with 400)
        success2, response2 = authenticated_client.post("/api/v1/vendor-skus/", sku_data, expected_status=400)
        
        # Verify error message is a STRING, not an object
        assert success2, f"Expected 400 status for duplicate: {response2}"
        assert "detail" in response2, f"Response should have 'detail' field: {response2}"
        
        detail = response2["detail"]
        assert isinstance(detail, str), f"Error detail should be a string, got {type(detail)}: {detail}"
        assert "already exists" in detail.lower(), f"Error should mention 'already exists': {detail}"
        
        # Cleanup - delete the test SKU
        if success1 and "id" in response1:
            authenticated_client.delete(f"/api/v1/vendor-skus/{response1['id']}")
    
    @pytest.mark.regression
    def test_vendor_sku_validation_error_returns_readable_format(self, authenticated_client, test_prefix):
        """
        Verifies that validation errors are returned in a format the frontend can parse.
        """
        # Send invalid data (missing required 'name' field)
        invalid_data = {
            "vendor": "Test Vendor",
            "sku": f"{test_prefix}-INVALID-001"
            # Missing 'name' which is required
        }
        
        success, response = authenticated_client.post(
            "/api/v1/vendor-skus/", 
            invalid_data,
            expected_status=422  # Validation error
        )
        
        # The response should be parseable - either a string detail or a structured validation error
        assert success, f"Expected 422 validation error: {response}"
        assert "detail" in response, f"Response should have 'detail' field: {response}"
        
        # FastAPI validation errors come as a list, which is fine
        # The key is that it's not an unparseable object
        detail = response["detail"]
        if isinstance(detail, list):
            # FastAPI validation format - frontend handles this
            assert len(detail) > 0, "Validation error list should not be empty"
            assert "msg" in detail[0] or "message" in detail[0], f"Validation item should have msg: {detail[0]}"
        elif isinstance(detail, str):
            # String format - also fine
            assert len(detail) > 0, "Error message should not be empty"
        else:
            # Object format - must have extractable message
            assert isinstance(detail, dict), f"Detail should be dict if not string/list: {type(detail)}"
            assert "message" in detail or "error" in detail, \
                f"Object detail must have 'message' or 'error' key: {detail}"


@pytest.mark.regression
class TestAPIErrorResponseFormat:
    """
    REGRESSION: All API errors should return messages in a format the frontend can display.
    
    The frontend expects error.response.data.detail to be either:
    1. A string: "Error message here"
    2. An object with 'message' or 'error' key: {message: "...", error: "..."}
    3. A list of validation errors: [{msg: "...", loc: [...]}]
    
    Returning a plain object like {some_key: "value"} will display as [object Object].
    """
    
    @pytest.mark.regression
    def test_402_premium_feature_error_has_message_field(self, authenticated_client, test_user):
        """
        Verifies that 402 Payment Required errors include a 'message' field.
        """
        from app.core.database import SessionLocal
        from app.models.tenant import Tenant
        
        # Temporarily disable premium features
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
                Tenant.id == test_user["tenant"]["id"]
            ).first()
            original_features = tenant.subscription_features or {}
            tenant.subscription_features = {"sku_lookup": False}
            db.commit()
            
            # Try to access premium endpoint
            success, response = authenticated_client.get("/api/v1/vendor-skus/lookup", params={"sku": "TEST"})
            
            # Restore features
            tenant.subscription_features = original_features
            db.commit()
            
        finally:
            db.close()
        
        # Verify error format is frontend-parseable
        if not success:
            # Should be 402
            detail = response.get("detail", {})
            if isinstance(detail, dict):
                # Object format must have message/error
                assert "message" in detail or "error" in detail, \
                    f"402 error object must have 'message' or 'error' field: {detail}"
            elif isinstance(detail, str):
                # String format is fine
                assert len(detail) > 0, "Error message should not be empty"
            else:
                pytest.fail(f"Unexpected detail format: {type(detail)}: {detail}")
