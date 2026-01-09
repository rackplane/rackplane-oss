
import pytest
from app.api.v1.vendor_skus import VendorSKUCreate

@pytest.mark.integration
@pytest.mark.regression
def test_repro_import_failure(authenticated_client, test_user):
    """
    Reproduction test for "Failed to import: [object Object]" error.
    Mimics the exact payload sent by the frontend during Global Catalog import.
    """
    # Payload copied from frontend VendorSKUs.tsx handleProductImport
    payload = {
        "vendor": "FS.com",
        "sku": "21254-REPRO",
        "part_number": "N-Q28SFP28-PC03",
        "name": "100G QSFP28 to 4x25G SFP28 DAC Cable",
        "manufacturer": "FS.com",
        "asset_type": None,  # Frontend sends null explicitly
        "specifications": {"length": "3m", "speed": "100G"},
        "price_usd": None,
        "currency": "USD",
        "compatibility": {},
        "description": None,
        "datasheet_url": None,
        "vendor_url": None,
        "notes": "Imported from Global Catalog"
    }
    
    # Needs sku_lookup feature enabled
    from app.core.database import SessionLocal
    from app.models.tenant import Tenant
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(Tenant.id == test_user["tenant"]["id"]).first()
        tenant.subscription_features = {"sku_lookup": True}
        db.commit()
    finally:
        db.close()

    # authenticated_client.post returns (success, response_data)
    # The custom TestClient.post takes (url, data, ...) where data is the payload
    success, response = authenticated_client.post("/api/v1/vendor-skus/", payload, expected_status=201)
    
    print(f"\nRequest Success: {success}")
    print(f"Response Body: {response}")
    
    # We expect this to FAIL initially if there's a bug, or succeed if the bug is only in the frontend error handling.
    # But seeing the actual response body will tell us what the [object Object] was.
    assert success, f"Import failed with response: {response}"

@pytest.mark.integration
@pytest.mark.regression
def test_local_sku_creation_works_without_sku_lookup_feature(authenticated_client, test_user):
    """
    Test that creating LOCAL vendor SKUs is NOT gated by sku_lookup feature.
    
    This test documents the intentional separation between:
    - LOCAL SKU management (create, read, update, delete) - always available
    - GLOBAL Catalog access - gated by sku_lookup feature
    
    The sku_lookup feature controls access to the Global Catalog, not local
    tenant SKU management. This test verifies that local SKU creation works
    even when sku_lookup is disabled.
    """
    payload = {
        "vendor": "FS.com",
        "sku": "21254-REPRO-FAIL",
        "part_number": "N-Q28SFP28-PC03",
        "name": "100G QSFP28 to 4x25G SFP28 DAC Cable",
        "manufacturer": "FS.com",
        "asset_type": None,
        "specifications": {"length": "3m", "speed": "100G"},
        "price_usd": None,
        "currency": "USD",
        "compatibility": {},
        "description": None,
        "datasheet_url": None,
        "vendor_url": None,
        "notes": "Imported from Global Catalog"
    }
    
    # Ensure sku_lookup feature is DISABLED
    from app.core.database import SessionLocal
    from app.models.tenant import Tenant
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(Tenant.id == test_user["tenant"]["id"]).first()
        tenant.subscription_features = {"sku_lookup": False}
        db.commit()
    finally:
        db.close()

    # Creating LOCAL SKUs should STILL work (not gated by sku_lookup)
    # sku_lookup feature only gates GLOBAL catalog access
    success, response = authenticated_client.post("/api/v1/vendor-skus/", payload)
    
    print(f"\nRequest Success (Expected True for local SKUs): {success}")
    print(f"Response Body: {response}")
    
    # Local SKU creation should succeed regardless of sku_lookup feature
    assert success or response.get("id") is not None, \
        f"Local SKU creation should work even without sku_lookup feature. Got: {response}"
