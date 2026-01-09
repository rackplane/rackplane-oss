#!/usr/bin/env python3
"""
Validation script for Tenant UUID implementation.
Tests the key features without requiring full test environment.
"""

import sys
import os
import uuid as uuid_lib

# Add app to path - derive from script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)  # Script is in backend/scripts/
sys.path.insert(0, BACKEND_DIR)

def test_tenant_model():
    """Test 1: Verify Tenant model has uuid field"""
    print("Test 1: Checking Tenant model has uuid field...")
    try:
        from app.models.tenant import Tenant

        # Check if uuid field exists
        if hasattr(Tenant, 'uuid'):
            print("  ✓ Tenant.uuid field exists")
        else:
            print("  ✗ Tenant.uuid field NOT found")
            return False

        # Verify uuid_lib is imported
        import app.models.tenant as tenant_module
        if hasattr(tenant_module, 'uuid_lib'):
            print("  ✓ uuid_lib imported correctly")
        else:
            print("  ✗ uuid_lib NOT imported")
            return False

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_api_customer_model():
    """Test 2: Verify ApiCustomer model has tenant_id field"""
    print("\nTest 2: Checking ApiCustomer model...")
    try:
        from app.models.api_customer import ApiCustomer

        # Check if tenant_id field exists
        if hasattr(ApiCustomer, 'tenant_id'):
            print("  ✓ ApiCustomer.tenant_id field exists")
        else:
            print("  ✗ ApiCustomer.tenant_id field NOT found")
            return False

        # Check contribution tracking fields
        required_fields = ['contribution_count', 'contributor_since', 'is_lifetime_contributor']
        for field in required_fields:
            if hasattr(ApiCustomer, field):
                print(f"  ✓ ApiCustomer.{field} exists")
            else:
                print(f"  ✗ ApiCustomer.{field} NOT found")
                return False

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_provision_request_schema():
    """Test 3: Verify ProvisionRequest has tenant_uuid field"""
    print("\nTest 3: Checking ProvisionRequest schema...")
    try:
        from app.api.v1.provision import ProvisionRequest

        # Create a test instance
        test_data = {
            "api_key_hash": "test_hash",
            "customer_name": "Test Customer",
            "tenant_uuid": str(uuid_lib.uuid4())
        }

        request = ProvisionRequest(**test_data)

        if hasattr(request, 'tenant_uuid') and request.tenant_uuid == test_data['tenant_uuid']:
            print("  ✓ ProvisionRequest.tenant_uuid field works")
        else:
            print("  ✗ ProvisionRequest.tenant_uuid field NOT working")
            return False

        # Test without tenant_uuid (backwards compatibility)
        test_data_no_uuid = {
            "api_key_hash": "test_hash",
            "customer_name": "Test Customer"
        }
        request_no_uuid = ProvisionRequest(**test_data_no_uuid)

        if hasattr(request_no_uuid, 'tenant_uuid'):
            print("  ✓ ProvisionRequest works without tenant_uuid (backwards compatible)")
        else:
            print("  ✗ ProvisionRequest NOT backwards compatible")
            return False

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_catalog_sku_request_schema():
    """Test 4: Verify ProvisionCatalogSKURequest has tenant_uuid field"""
    print("\nTest 4: Checking ProvisionCatalogSKURequest schema...")
    try:
        from app.api.v1.provision import ProvisionCatalogSKURequest

        # Create a test instance
        test_data = {
            "vendor": "Dell",
            "sku": "TEST-SKU",
            "name": "Test Item",
            "tenant_uuid": str(uuid_lib.uuid4())
        }

        request = ProvisionCatalogSKURequest(**test_data)

        if hasattr(request, 'tenant_uuid') and request.tenant_uuid == test_data['tenant_uuid']:
            print("  ✓ ProvisionCatalogSKURequest.tenant_uuid field works")
        else:
            print("  ✗ ProvisionCatalogSKURequest.tenant_uuid field NOT working")
            return False

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_migration_exists():
    """Test 5: Verify migration file exists"""
    print("\nTest 5: Checking migration file...")
    try:
        migration_path = os.path.join(BACKEND_DIR, "alembic", "versions", "add_tenant_uuid.py")

        if os.path.exists(migration_path):
            print(f"  ✓ Migration file exists: {migration_path}")

            # Read and verify it has the upgrade function
            with open(migration_path, 'r') as f:
                content = f.read()
                if 'def upgrade()' in content and 'uuid' in content:
                    print("  ✓ Migration has upgrade function with uuid logic")
                else:
                    print("  ✗ Migration missing upgrade logic")
                    return False
        else:
            print(f"  ✗ Migration file NOT found: {migration_path}")
            return False

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all validation tests"""
    print("=" * 60)
    print("Tenant UUID Implementation Validation")
    print("=" * 60)

    tests = [
        test_tenant_model,
        test_api_customer_model,
        test_provision_request_schema,
        test_catalog_sku_request_schema,
        test_migration_exists
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All validation tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
