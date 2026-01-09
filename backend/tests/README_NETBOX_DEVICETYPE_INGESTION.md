# NetBox Device Type Ingestion Integration Tests

## Overview

This test suite (`test_netbox_devicetype_ingestion_pytest.py`) provides comprehensive integration testing for the NetBox Device Type Library YAML ingestion feature.

## Test Strategy

### Database Setup
- **Real PostgreSQL Database**: Tests run against a real PostgreSQL 17 database (not mocks)
- **Alembic Migrations**: Database schema is created via `alembic upgrade head` before tests run
- **Transaction Isolation**: Each test runs in a transaction that rolls back automatically
- **No Data Persistence**: Tests never affect production data or persist test data

### Test Data
- **Real YAML Files**: Uses actual NetBox device type YAML files in `tests/data/`:
  - `5912-54X-O-AC-F.yaml` (Arista switch)
  - `AS7326-56X-O-AC-F.yaml` (Edgecore switch)
  - `N9K-C92160YC-X.yaml` (Cisco Nexus switch)
  - `PowerEdge-R730.yaml` (Dell server)

### What's Tested

#### ✅ Core Field Mapping
- `manufacturer` → `VendorSKU.manufacturer`
- `model` → `VendorSKU.name`
- `u_height` → `specifications['u_height']` (JSONB)
- `weight` → `specifications['weight_kg']` (JSONB)

#### ✅ JSONB Specifications Storage
- Interfaces data preserved in `specifications['interface_details']`
- Power ports counted and stored in `specifications['power_ports']`
- Console ports tracked in `specifications['console_ports']`
- All non-core fields preserved in JSONB column

#### ✅ Edge Cases
- **Missing weight field**: Handles gracefully without errors
- **Duplicate imports**: Enforces unique constraint (tenant + vendor + SKU)
- **Empty specifications**: Allows minimal device types
- **Tenant isolation**: Verifies multi-tenant data separation

#### ✅ PostgreSQL JSONB Features
- JSONB field queries (e.g., `specifications['u_height'] = 1`)
- Nested value filtering
- Type-safe JSONB operations

#### ✅ Business Logic
- **Asset type inference**: Automatically detects switch/server/router/etc.
- **Interface counting**: Accurately counts and categorizes network ports
- **Data integrity**: Validates all transformations preserve source data

## Running the Tests

### Prerequisites

```bash
# Ensure backend services are running
docker compose up -d db backend

# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio
```

### Run All Ingestion Tests

```bash
# From backend directory
cd backend

# Run the full ingestion test suite
pytest tests/test_netbox_devicetype_ingestion_pytest.py -v

# Run with detailed output
pytest tests/test_netbox_devicetype_ingestion_pytest.py -vv -s

# Run specific test
pytest tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping -v
```

### Run with Coverage

```bash
pytest tests/test_netbox_devicetype_ingestion_pytest.py --cov=app.services.devicetype_mapper --cov=app.services.devicetype_service --cov-report=html
```

### Run Parameterized Tests for Specific Files

```bash
# Test only Cisco device
pytest tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[N9K-C92160YC-X.yaml-Cisco] -v

# Test only Dell device
pytest tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[PowerEdge-R730.yaml-Dell] -v
```

## Test Cases

### 1. `test_device_type_core_field_mapping`
**Parameterized**: Runs for all 4 YAML files
**Purpose**: Verifies core fields map correctly
**Assertions**:
- ✅ Manufacturer stored correctly
- ✅ Model name in `name` field
- ✅ Vendor is "NetBox Library"
- ✅ SKU has "netbox_" prefix
- ✅ U-height in JSONB specifications
- ✅ Weight in JSONB specifications (as weight_kg)

### 2. `test_device_type_jsonb_specifications_storage`
**Parameterized**: Runs for all 4 YAML files
**Purpose**: Verifies non-core data stored in JSONB
**Assertions**:
- ✅ specifications is valid dict
- ✅ Interface count matches YAML
- ✅ Interface details summary present
- ✅ Power ports counted correctly
- ✅ Console ports counted correctly

### 3. `test_missing_weight_field`
**Purpose**: Tests edge case of missing optional field
**Assertions**:
- ✅ Import succeeds despite missing weight
- ✅ weight_kg not in specifications (or is None/0)
- ✅ Other fields still work correctly

### 4. `test_duplicate_device_type_import`
**Purpose**: Tests unique constraint enforcement
**Assertions**:
- ✅ First import succeeds
- ✅ Second import raises IntegrityError
- ✅ Error is unique constraint violation

### 5. `test_empty_specifications_scenario`
**Purpose**: Tests minimal device type with few fields
**Assertions**:
- ✅ Can create with minimal data
- ✅ specifications can be empty dict
- ✅ Core fields still required

### 6. `test_jsonb_query_capabilities`
**Purpose**: Tests PostgreSQL JSONB query features
**Assertions**:
- ✅ Can filter by JSONB field values
- ✅ JSONB queries return correct results
- ✅ Type casting works in queries

### 7. `test_asset_type_inference`
**Purpose**: Tests automatic asset type detection
**Assertions**:
- ✅ Cisco Nexus detected as "switch"
- ✅ Dell PowerEdge detected as "server"
- ✅ Asset type stored correctly

### 8. `test_interface_count_accuracy`
**Purpose**: Tests interface counting and categorization
**Assertions**:
- ✅ network_ports count matches YAML
- ✅ interface_details breakdown present
- ✅ Counts accessible via JSONB queries

### 9. `test_tenant_isolation`
**Purpose**: Tests multi-tenant data separation
**Assertions**:
- ✅ VendorSKUs are tenant-scoped
- ✅ Same device can exist in multiple tenants
- ✅ Queries respect tenant boundaries

## Fixtures Used

### From `conftest.py`

#### `db_session`
- **Type**: Function-scoped
- **Purpose**: Provides transaction-isolated database session
- **Behavior**: Automatically rolls back after each test

#### `load_device_yaml`
- **Type**: Function-scoped factory
- **Purpose**: Loads YAML files from `tests/data/`
- **Usage**: `yaml_data = load_device_yaml("N9K-C92160YC-X.yaml", manufacturer="Cisco")`
- **Returns**: Python dict with `_metadata` added

#### `sample_yaml_files`
- **Type**: Function-scoped
- **Purpose**: List of (filename, manufacturer) tuples for parameterized tests
- **Returns**: `[("5912-54X-O-AC-F.yaml", "Arista"), ...]`

#### `test_tenant`
- **Type**: Function-scoped
- **Purpose**: Creates isolated test tenant with unique name
- **Cleanup**: Automatically deleted after test (cascades to all data)

#### `api_client` / `admin_token`
- **Type**: Session-scoped
- **Purpose**: Provides authenticated API client for API tests

## Expected Test Output

```
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[5912-54X-O-AC-F.yaml-Arista] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[AS7326-56X-O-AC-F.yaml-Edgecore] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[N9K-C92160YC-X.yaml-Cisco] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_core_field_mapping[PowerEdge-R730.yaml-Dell] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_jsonb_specifications_storage[5912-54X-O-AC-F.yaml-Arista] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_jsonb_specifications_storage[AS7326-56X-O-AC-F.yaml-Edgecore] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_jsonb_specifications_storage[N9K-C92160YC-X.yaml-Cisco] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_device_type_jsonb_specifications_storage[PowerEdge-R730.yaml-Dell] PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_missing_weight_field PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_duplicate_device_type_import PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_empty_specifications_scenario PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_jsonb_query_capabilities PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_asset_type_inference PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_interface_count_accuracy PASSED
tests/test_netbox_devicetype_ingestion_pytest.py::TestNetBoxDeviceTypeIngestion::test_tenant_isolation PASSED

======================== 15 passed in 12.34s ========================
```

## Debugging Failed Tests

### View SQL Queries
```bash
# Set echo=True in engine config (edit conftest.py temporarily)
# Or set environment variable:
SQLALCHEMY_ECHO=1 pytest tests/test_netbox_devicetype_ingestion_pytest.py -v
```

### Inspect JSONB Content
```python
# In failed test, add:
import json
print(json.dumps(vendor_sku.specifications, indent=2))
```

### Check Database State
```bash
# Connect to test database during test run
docker compose exec db psql -U dcms -d datacenter_inventory

# View VendorSKU records
SELECT id, manufacturer, name, specifications->'u_height' as u_height
FROM vendor_skus
WHERE vendor = 'NetBox Library';
```

## Common Issues

### Issue: "FileNotFoundError: Test data file not found"
**Solution**: Ensure YAML files exist in `backend/tests/data/`

### Issue: "IntegrityError: null value in column 'tenant_id'"
**Solution**: Ensure `test_tenant` fixture is used in test function signature

### Issue: "Transaction rollback didn't happen"
**Solution**: Check that test uses `db_session` fixture, not a custom session

### Issue: "JSONB query returns no results"
**Solution**: Use `.astext` for string comparison: `specifications['u_height'].astext == '1'`

## Maintenance

### Adding New Test Data Files
1. Download YAML from https://github.com/netbox-community/devicetype-library
2. Save to `backend/tests/data/`
3. Add to `sample_yaml_files` fixture in `conftest.py`
4. Tests will automatically include the new file

### Updating Expected Values
If NetBox YAML format changes, update assertions in:
- `DeviceTypeMapper._build_specifications()` (update mapping logic)
- Test assertions (update expected field names)

## Related Documentation
- [DeviceTypeService](../app/services/devicetype_service.py) - GitHub API client
- [DeviceTypeMapper](../app/services/devicetype_mapper.py) - YAML transformation logic
- [VendorSKU Model](../app/models/vendor_sku.py) - Database model
- [Feature Documentation](../../docs/features/netbox-devicetype-import.md) - User guide
