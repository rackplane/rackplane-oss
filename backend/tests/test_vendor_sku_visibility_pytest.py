import pytest
from app.models.catalog_sku import CatalogSKU
from datetime import datetime
import uuid

@pytest.mark.integration
@pytest.mark.regression
def test_new_tenant_sees_no_vendor_skus(authenticated_client, db_session):
    """
    Regression Test: A new tenant should not see any vendor SKUs by default.
    Previously, they were seeing the entire Global Catalog (CatalogSKU).
    """
    # 1. Setup: Ensure there is at least one Global Catalog SKU
    unique_sku = f"GLOBAL-TEST-{uuid.uuid4()}"
    global_sku = CatalogSKU(
        vendor="GlobalVendor",
        sku=unique_sku,
        name="Global Item",
        is_active=True,
        vertical="datacenter",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(global_sku)
    db_session.commit()
    
    # 2. Action: Call the list endpoint with the authenticated client (which is a new tenant/user)
    # Note: TestClient in this codebase returns (success, data) tuple, not Response object
    success, data = authenticated_client.get("/api/v1/vendor-skus/")
    
    # Check for success
    assert success is True, f"API Request failed: {data}"
    
    # data is the list of SKUs
    assert isinstance(data, list), "Expected list of SKUs"
    
    # 3. Assertion: Should be empty (or at least NOT contain the Global SKU)
    global_items = [item for item in data if item.get('sku') == unique_sku]
    
    # This assertion will FAIL if the bug is present
    assert len(global_items) == 0, f"Found Global Catalog SKU in default specific list! Access should be searched/opt-in. Found: {global_items}"
