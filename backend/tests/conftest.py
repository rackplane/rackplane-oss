"""
Pytest configuration and shared fixtures for DCMS test suite.

This module provides fixtures for:
- API client (TestClient wrapper)
- Authentication tokens (admin and test user)
- Test tenant and user creation
- Test data management
"""

import os
import pytest
import time
from typing import Generator, Dict, Any, Optional
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import TestClient from existing test_suite
from test_suite import TestClient, BASE_URL

# Import demo database fixtures (pytest will auto-discover fixtures in this module)
# The fixtures are defined in tests/fixtures/demo_database.py and will be
# automatically available when that module is imported
try:
    from .fixtures import demo_database  # noqa: F401
except ImportError:
    # Fixtures may not be available in all environments
    pass

# Configuration
# Default admin credentials (same as bootstrap.py and production defaults)
# These can be overridden via environment variables:
#   TEST_ADMIN_USERNAME - defaults to "admin"
#   TEST_ADMIN_PASSWORD - defaults to "ChangeMe123!"
TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "ChangeMe123!")
API_BASE_URL = os.getenv("API_URL", BASE_URL)


@pytest.fixture(scope="function")
def db_session():
    """
    Database session fixture for tests that need direct database access.
    
    Provides a SQLAlchemy session that auto-closes after the test.
    Use this for unit tests that interact with the database directly
    (not via API endpoints).
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for API testing"""
    return API_BASE_URL


@pytest.fixture(scope="session")
def api_client(api_base_url: str) -> TestClient:
    """
    HTTP client for API testing.
    
    This fixture wraps the existing TestClient class from test_suite.py
    to maintain compatibility with existing test patterns.
    """
    return TestClient(base_url=api_base_url)


@pytest.fixture(scope="session")
def admin_credentials() -> Dict[str, str]:
    """Admin credentials for super admin operations"""
    return {
        "username": TEST_ADMIN_USERNAME,
        "password": TEST_ADMIN_PASSWORD
    }


@pytest.fixture(scope="session")
def admin_token(api_client: TestClient, admin_credentials: Dict[str, str]) -> Optional[str]:
    """
    Super admin authentication token.
    
    This fixture attempts to login as super admin. If login fails,
    it bootstraps the admin user using the same logic as bootstrap.py.
    Uses default credentials: admin / ChangeMe123!
    """
    # Try to login first
    token = api_client.login(
        admin_credentials["username"],
        admin_credentials["password"]
    )
    
    if token:
        # Even if login succeeds, ensure sequence is synced to prevent collisions
        # because previous runs might have manually inserted ID=1 without updating sequence
        try:
            from app.core.database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            try:
                db.execute(text("SELECT setval('tenants_id_seq', (SELECT MAX(id) FROM tenants))"))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Warning: Failed to sync sequences: {e}")
        return token
    
    # If login fails, bootstrap admin user via database
    # This uses the same approach as bootstrap.py for consistency
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.models.tenant import Tenant
        from app.models.user_role import UserRole
        from app.core.auth import get_password_hash
        
        db = SessionLocal()
        try:
            # Ensure admin tenant exists (tenant ID 1)
            admin_tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(Tenant.id == 1).first()
            if not admin_tenant:
                admin_tenant = Tenant(
                    id=1,  # Explicitly set ID 1 for admin tenant
                    name="Admin Tenant",
                    slug="admin",
                    subscription_tier="standard",
                    is_active=True
                )
                db.add(admin_tenant)
                db.commit()
                db.refresh(admin_tenant)
                # Reset sequence to ensure next tenant gets ID 2
                from sqlalchemy import text
                db.execute(text("SELECT setval('tenants_id_seq', (SELECT MAX(id) FROM tenants))"))
                db.commit()
            
            # Check if admin user exists
            admin_user = db.query(User).execution_options(skip_tenant_filter=True).filter(
                User.username == TEST_ADMIN_USERNAME
            ).first()
            
            if admin_user:
                # Update existing admin user to ensure correct credentials and role
                admin_user.hashed_password = get_password_hash(TEST_ADMIN_PASSWORD)
                admin_user.is_active = True
                admin_user.role = UserRole.SUPER_ADMIN
                admin_user.is_super_admin = True
                if hasattr(admin_user, 'sync_is_super_admin'):
                    admin_user.sync_is_super_admin()
                db.commit()
                db.refresh(admin_user)
            else:
                # Create new admin user (same logic as bootstrap.py)
                admin_user = User(
                    username=TEST_ADMIN_USERNAME,
                    hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
                    is_active=True,
                    tenant_id=admin_tenant.id,
                    role=UserRole.SUPER_ADMIN,
                    is_super_admin=True
                )
                if hasattr(admin_user, 'sync_is_super_admin'):
                    admin_user.sync_is_super_admin()
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
            
            # Try login with bootstrapped user
            token = api_client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
            if token:
                return token
            else:
                # If login still fails, there might be an auth issue
                print(f"Warning: Admin user exists but login failed. User ID: {admin_user.id}, Active: {admin_user.is_active}, Super Admin: {admin_user.is_super_admin}")
        finally:
            db.close()
    except Exception as e:
        # Log the error but don't fail immediately
        import traceback
        print(f"Error bootstrapping admin user: {e}")
        traceback.print_exc()
    
    # If we still don't have a token, skip tests that require admin
    pytest.skip("Failed to authenticate as super admin. Please ensure admin user exists.")


@pytest.fixture(scope="function")
def test_tenant(admin_token: str, api_client: TestClient) -> Generator[Dict[str, Any], None, None]:
    """
    Create an isolated test tenant for each test function.
    
    This fixture:
    1. Creates a unique test tenant (always with PYTEST- prefix)
    2. Yields tenant data
    3. Cleans up tenant after test (cascades to all data)
    
    IMPORTANT: Never uses production tenants (IDs 1, 2, 3 or slugs: default, sonn, netdef)
    
    Scope: function (each test gets a fresh tenant)
    """
    import uuid
    # Use UUID to ensure uniqueness even with parallel execution
    unique_id = str(uuid.uuid4())[:8]
    test_prefix = f"PYTEST-{int(time.time())}-{os.getpid()}-{unique_id}"
    
    # Set admin token
    api_client.set_token(admin_token)
    
    # Create test tenant (always with PYTEST- prefix to avoid production tenants)
    tenant_data = {
        "name": f"{test_prefix}-Test-Tenant",
        "slug": f"{test_prefix.lower()}-test-tenant",
        "subscription_tier": "pro",  # Use "pro" tier to allow multiple test users (community/starter only allow 1 user)
        "contact_email": f"test-{test_prefix.lower()}@test.example.com"
    }
    
    success, tenant_response = api_client.post("/api/v1/tenants/", tenant_data, expected_status=201)
    
    if not success or "id" not in tenant_response:
        pytest.fail(f"Failed to create test tenant: {tenant_response}")
    
    # Safety check: Ensure we didn't accidentally get a production tenant
    # Check slug/name first - if it has PYTEST prefix, it's safe even if ID matches production
    tenant_slug = tenant_response.get('slug', '').lower()
    tenant_name = tenant_response.get('name', '').upper()
    
    # If slug/name has PYTEST prefix, it's a test tenant (safe)
    is_test_tenant = 'pytest' in tenant_slug or 'PYTEST' in tenant_name
    
    # Production tenant identifiers
    PRODUCTION_TENANT_IDS = [1, 2, 3, 778]  # Admin Tenant, SONN, netdef, HedgeHog
    PRODUCTION_TENANT_SLUGS = ['admin', 'sonn', 'netdef', 'hedgehog']
    
    # Only fail if:
    # 1. It's NOT a test tenant (no PYTEST prefix) AND
    # 2. It matches a production ID or slug
    if not is_test_tenant and (tenant_response['id'] in PRODUCTION_TENANT_IDS or tenant_slug in PRODUCTION_TENANT_SLUGS):
        pytest.fail(f"ERROR: Test fixture accidentally created/used production tenant! ID: {tenant_response['id']}, Slug: {tenant_response.get('slug')}")
    
    yield tenant_response
    
    # Cleanup: Delete tenant (cascades to all data)
    try:
        api_client.set_token(admin_token)
        api_client.delete(f"/api/v1/tenants/{tenant_response['id']}", expected_status=204)
    except Exception as e:
        # Log but don't fail test if cleanup fails
        print(f"Warning: Failed to cleanup test tenant {tenant_response['id']}: {e}")


@pytest.fixture(scope="function")
def test_user(test_tenant: Dict[str, Any], admin_token: str, api_client: TestClient) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test user in the test tenant.
    
    This fixture:
    1. Creates a test user in the test tenant
    2. Logs in to get authentication token
    3. Yields user data and token
    4. Cleanup handled by tenant deletion (cascade)
    
    Scope: function (each test gets a fresh user)
    """
    import uuid
    # Use UUID to ensure uniqueness
    unique_id = str(uuid.uuid4())[:8]
    test_prefix = f"PYTEST-{int(time.time())}-{os.getpid()}-{unique_id}"
    
    # Set admin token
    api_client.set_token(admin_token)
    
    # Create test user
    user_data = {
        "username": f"{test_prefix.lower()}-testuser",
        "password": "TestPassword123!",
        "tenant_id": test_tenant["id"],
        "role": "tenant_admin"
    }
    
    success, user_response = api_client.post(
        f"/api/v1/tenants/{test_tenant['id']}/users",
        user_data,
        expected_status=201
    )
    
    if not success or "id" not in user_response:
        pytest.fail(f"Failed to create test user: {user_response}")
    
    # Login to get token
    token = api_client.login(user_data["username"], user_data["password"])
    
    if not token:
        pytest.fail("Failed to login as test user")
    
    yield {
        "user": user_response,
        "token": token,
        "credentials": user_data,
        "tenant": test_tenant
    }
    
    # Cleanup handled by tenant deletion (cascade)


@pytest.fixture(scope="function")
def authenticated_client(test_user: Dict[str, Any], api_client: TestClient) -> TestClient:
    """
    API client authenticated as test user.
    
    This fixture sets the authentication token on the API client
    and returns it ready for use in tests.
    
    Scope: function (each test gets a fresh authenticated client)
    """
    api_client.set_token(test_user["token"])
    return api_client


@pytest.fixture(scope="function")
def regular_user(test_tenant: Dict[str, Any], admin_token: str, api_client: TestClient) -> Generator[Dict[str, Any], None, None]:
    """
    Create a regular (non-admin) user in the test tenant.
    
    Role: "user"
    Scope: function (each test gets a fresh user)
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    test_prefix = f"PYTEST-USER-{int(time.time())}-{os.getpid()}-{unique_id}"
    
    # Set admin token to create user
    api_client.set_token(admin_token)
    
    # Create regular user
    user_data = {
        "username": f"{test_prefix.lower()}-regular",
        "password": "TestPassword123!",
        "tenant_id": test_tenant["id"],
        "role": "user"  # Regular user role
    }
    
    success, user_response = api_client.post(
        f"/api/v1/tenants/{test_tenant['id']}/users",
        user_data,
        expected_status=201
    )
    
    if not success or "id" not in user_response:
        pytest.fail(f"Failed to create regular user: {user_response}")
    
    # Login to get token
    token = api_client.login(user_data["username"], user_data["password"])
    
    if not token:
        pytest.fail("Failed to login as regular user")
    
    yield {
        "user": user_response,
        "token": token,
        "credentials": user_data,
        "tenant": test_tenant
    }


@pytest.fixture(scope="function")
def regular_user_client(regular_user: Dict[str, Any], api_client: TestClient) -> TestClient:
    """
    API client authenticated as a regular (non-admin) user.
    """
    api_client.set_token(regular_user["token"])
    return api_client


@pytest.fixture(scope="function")
def ensure_asset_types(authenticated_client, test_tenant):
    """
    Ensure common asset types exist for the test tenant.
    This fixture runs before tests that need asset types.
    """
    from app.core.database import SessionLocal
    from app.models.asset_type import AssetTypeModel
    from app.core.tenant import set_current_tenant_id
    
    # Set tenant context before querying
    tenant_id = test_tenant["id"]
    set_current_tenant_id(tenant_id)
    
    db = SessionLocal()
    try:
        common_types = [
            ("server_device", "Server Device", "Server hardware"),
            ("network_device", "Network Device", "Network switch or router"),
            ("storage_box", "Storage Box", "Storage container for inventory"),
            ("dac_cable", "DAC Cable", "Direct Attach Copper cable"),
            ("fiber_cable", "Fiber Cable", "Fiber optic cable"),
            ("ethernet_cable", "Ethernet Cable", "Ethernet network cable"),
        ]
        
        for name, display_name, description in common_types:
            # Query directly with tenant_id filter (more explicit and avoids context issues)
            query = db.query(AssetTypeModel).filter(
                AssetTypeModel.name == name,
                AssetTypeModel.tenant_id == tenant_id
            )
            asset_type = query.first()
            
            if not asset_type:
                asset_type = AssetTypeModel(
                    name=name,
                    display_name=display_name,
                    description=description,
                    tenant_id=tenant_id,
                    is_active=True
                )
                db.add(asset_type)
        
        db.commit()
    finally:
        db.close()
        # Clear tenant context after use
        from app.core.tenant import clear_tenant_id
        clear_tenant_id()


@pytest.fixture(scope="function")
def test_prefix() -> str:
    """
    Generate a unique test prefix for each test.
    
    This helps identify test data and ensures uniqueness.
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return f"PYTEST-{int(time.time())}-{os.getpid()}-{unique_id}"


@pytest.fixture(scope="session", autouse=True)
def backup_before_tests(request):
    """
    Session-scoped fixture that creates a backup before any tests run.
    
    This fixture:
    1. Runs automatically (autouse=True) at the start of the test session
    2. Creates a full database backup before any tests run
    3. Stores backup path for potential restore after tests
    
    This protects production data from being deleted by tests that use clear_existing=True.
    
    NOTE: Skipped in CI environments (GitHub Actions) where there's no real data to protect.
    """
    import json
    from pathlib import Path
    from datetime import datetime
    
    # Skip backup in CI environments - there's no real data to protect
    # CI uses a fresh database for each run
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        print("\n" + "="*60)
        print("ℹ️  Skipping pre-test backup (CI environment detected)")
        print("="*60 + "\n")
        yield
        return
    
    # Create backup before tests
    backup_dir = Path("/tmp/pytest_backups")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"pre_test_backup_{timestamp}.json"
    
    try:
        from app.core.database import SessionLocal
        from app.services.backup_service import BackupService
        
        db = SessionLocal()
        try:
            print("\n" + "="*60)
            print("Creating pre-test backup to protect existing data...")
            backup_data = BackupService.export_database(db, skip_tenant_filter=True)
            
            # Save backup
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            # Count items in backup
            total_assets = 0
            if 'tables' in backup_data and 'assets' in backup_data['tables']:
                assets_table = backup_data['tables']['assets']
                if 'data' in assets_table:
                    total_assets = len(assets_table['data'])
            
            print(f"✓ Backup created: {backup_path}")
            print(f"  Assets in backup: {total_assets}")
            print("="*60 + "\n")
            
            # Store backup path for potential restore
            request.config._pytest_backup_path = str(backup_path)
        finally:
            db.close()
    except Exception as e:
        # Don't fail tests if backup fails, but warn
        print(f"\n⚠ WARNING: Failed to create pre-test backup: {e}")
        print("⚠ Tests that clear data may delete production data!")
        import traceback
        traceback.print_exc()
    
    yield  # Run all tests
    
    # After tests, automatically restore the database state
    # Restore database from backup if it exists
    backup_path = getattr(request.config, '_pytest_backup_path', None) # Use _pytest_backup_path as set during backup
    if backup_path and os.path.exists(backup_path):
        try:
            from app.core.database import SessionLocal
            from app.services.backup_service import BackupService
            import json
            
            db = SessionLocal()
            try:
                print("\n" + "="*60)
                print("♻️  Automatically restoring pre-test database state...")
                
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                
                # Use clear_existing=True to wipe all data created during tests
                # and restore the exact state from before the session started.
                result = BackupService.import_database(db, backup_data, clear_existing=True)
                
                if result.get('errors'):
                    print(f"⚠️  Restore completed with {len(result['errors'])} errors")
                else:
                    print("✅ Database successfully restored to clean pre-test state")
                print("="*60 + "\n")
                
                # Optional: Remove the temporary backup file after successful restoration
                try:
                    os.remove(backup_path)
                except Exception:
                    pass
            finally:
                db.close()
        except Exception as e:
            print(f"\n⚠ WARNING: Failed to automatically restore database: {e}")
            import traceback
            traceback.print_exc()


@pytest.fixture(scope="session", autouse=True)
def cleanup_orphaned_test_tenants(request):
    """
    Session-scoped fixture that runs cleanup after all tests complete.

    This fixture:
    1. Runs automatically (autouse=True) at the end of the test session
    2. Cleans up any orphaned test tenants that weren't properly deleted
    3. Handles cases where tests fail or are interrupted

    Scope: session (runs once after all tests)
    """
    yield  # Run all tests first

    # Cleanup after all tests complete
    try:
        # Import cleanup function from parent directory
        import importlib.util
        cleanup_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cleanup_test_tenants.py")
        spec = importlib.util.spec_from_file_location("cleanup_test_tenants", cleanup_path)
        cleanup_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cleanup_module)

        print("\n" + "="*60)
        print("Running final cleanup of orphaned test tenants...")
        cleanup_module.cleanup_test_tenants()
        print("="*60)

        # Show backup location if it exists
        backup_path = getattr(request.config, '_pytest_backup_path', None)
        if backup_path:
            print(f"\nPre-test backup available at: {backup_path}")
            print("To restore: docker compose exec backend python restore_cli.py restore {backup_path} --clear")
    except Exception as e:
        # Don't fail the test session if cleanup fails
        print(f"\nWarning: Failed to run final cleanup: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# NetBox Device Type YAML Testing Fixtures
# ============================================================================

@pytest.fixture
def load_device_yaml():
    """
    Factory fixture to load NetBox device type YAML files from tests/data.

    Usage:
        yaml_data = load_device_yaml("N9K-C92160YC-X.yaml")

    Args:
        filename: Name of the YAML file in tests/data directory

    Returns:
        Parsed YAML data as Python dict with manufacturer metadata added

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML is malformed
    """
    import yaml
    from pathlib import Path

    test_data_dir = Path(__file__).parent / "data"

    def _load(filename: str, manufacturer: str = None) -> Dict[str, Any]:
        yaml_path = test_data_dir / filename

        if not yaml_path.exists():
            raise FileNotFoundError(f"Test data file not found: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in {filename}: expected dict, got {type(data)}")

        # Add metadata that the service would normally add
        if manufacturer:
            slug = filename.replace('.yaml', '').replace('.yml', '')
            data['_metadata'] = {
                'manufacturer': manufacturer,
                'slug': slug,
                'source': 'netbox-community/devicetype-library'
            }

        return data

    return _load


@pytest.fixture
def sample_yaml_files() -> list[tuple[str, str]]:
    """
    List of sample YAML files with their manufacturers for parameterized tests.

    Returns:
        List of tuples: (filename, manufacturer_name)
    """
    return [
        ("5912-54X-O-AC-F.yaml", "Arista"),
        ("AS7326-56X-O-AC-F.yaml", "Edgecore"),
        ("N9K-C92160YC-X.yaml", "Cisco"),
        ("PowerEdge-R730.yaml", "Dell"),
    ]

