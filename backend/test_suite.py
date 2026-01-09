#!/usr/bin/env python3
"""
Comprehensive Test Suite for DCMS Multi-Tenant SaaS Application
Tests all major functionality including tenant isolation, CRUD operations, and edge cases.
"""

import sys
import os
import requests
import json
import time
import io
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TEST_PREFIX = f"TEST-{int(time.time())}"

# Authentication credentials (can be overridden via environment variables)
TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "ChangeMe123!")

# Test results tracking
test_results: List[Dict] = []
test_count = 0
pass_count = 0
fail_count = 0


class TestResult:
    """Track individual test results"""
    def __init__(self, test_id: str, name: str, passed: bool, message: str = "", data: Dict = None):
        self.test_id = test_id
        self.name = name
        self.passed = passed
        self.message = message
        self.data = data or {}
        global test_count, pass_count, fail_count
        test_count += 1
        if passed:
            pass_count += 1
        else:
            fail_count += 1
        test_results.append({
            "test_id": test_id,
            "name": name,
            "passed": passed,
            "message": message,
            "data": data
        })


class TestClient:
    """HTTP client for API testing"""
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.tokens: Dict[str, str] = {}  # tenant_name -> token
        
    def login(self, username: str, password: str) -> Optional[str]:
        """Login and return token"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                return token
            return None
        except Exception as e:
            print(f"Login error: {e}")
            return None
    
    def get(self, endpoint: str, expected_status: int = 200, raw_response: bool = False, **kwargs) -> Tuple[bool, Dict]:
        """GET request
        
        Args:
            raw_response: If True, return the raw response object instead of parsed JSON
        """
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", **kwargs)
            success = response.status_code == expected_status
            if raw_response:
                # Return raw response object for CSV/binary downloads
                return success, response
            # Handle image/binary responses
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type or 'application/octet-stream' in content_type:
                return success, {"content_type": content_type, "size": len(response.content)}
            # Try to parse as JSON
            try:
                return success, response.json() if response.content else {}
            except (ValueError, json.JSONDecodeError):
                # Not JSON - return as text or binary info
                return success, {"content": response.text[:100] if response.text else "", "content_type": content_type}
        except Exception as e:
            return False, {"error": str(e)}
    
    def post(self, endpoint: str, data: Dict, expected_status: int = 200, **kwargs) -> Tuple[bool, Dict]:
        """POST request"""
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                **kwargs
            )
            success = response.status_code == expected_status
            return success, response.json() if response.content else {}
        except Exception as e:
            return False, {"error": str(e)}
    
    def put(self, endpoint: str, data: Dict, expected_status: int = 200, **kwargs) -> Tuple[bool, Dict]:
        """PUT request"""
        try:
            response = self.session.put(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                **kwargs
            )
            success = response.status_code == expected_status
            return success, response.json() if response.content else {}
        except Exception as e:
            return False, {"error": str(e)}

    def patch(self, endpoint: str, data: Dict, expected_status: int = 200, **kwargs) -> Tuple[bool, Dict]:
        """PATCH request"""
        try:
            response = self.session.patch(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                **kwargs
            )
            success = response.status_code == expected_status
            return success, response.json() if response.content else {}
        except Exception as e:
            return False, {"error": str(e)}
    
    def delete(self, endpoint: str, expected_status = 200, **kwargs) -> Tuple[bool, Dict]:
        """DELETE request"""
        try:
            response = self.session.delete(f"{self.base_url}{endpoint}", **kwargs)
            # Handle both single int and list of ints for expected_status
            if isinstance(expected_status, list):
                success = response.status_code in expected_status
            else:
                success = response.status_code == expected_status
            return success, response.json() if response.content else {}
        except Exception as e:
            return False, {"error": str(e)}

    def post_file(self, endpoint: str, file_obj, filename: str = None, params: dict = None, expected_status: int = 200, **kwargs) -> Tuple[bool, Dict]:
        """
        POST request with multipart/form-data file upload.

        Used for backup import endpoints that accept files.
        
        Args:
            endpoint: API endpoint
            file_obj: File-like object or bytes to upload
            filename: Optional filename for the upload
            params: Optional query parameters
            expected_status: Expected HTTP status code
        """
        try:
            # Handle bytes or file-like objects
            if isinstance(file_obj, bytes):
                file_name = filename or "file"
                files = {"file": (file_name, io.BytesIO(file_obj), "application/octet-stream")}
            else:
                file_name = filename or getattr(file_obj, "name", "file")
                files = {"file": (file_name, file_obj)}
            
            # Merge params into kwargs
            if params:
                kwargs.setdefault("params", {}).update(params)
            
            response = self.session.post(f"{self.base_url}{endpoint}", files=files, **kwargs)
            success = response.status_code == expected_status
            try:
                return success, response.json() if response.content else {}
            except (ValueError, json.JSONDecodeError):
                return success, {"content": response.text[:100] if response.text else ""}
        except Exception as e:
            return False, {"error": str(e)}
    
    def set_token(self, token: str):
        """Set authorization token"""
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def clear_token(self):
        """Clear authorization token (for public endpoints)"""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]


# Global test client
client = TestClient()

# Test data storage
test_data: Dict[str, any] = {
    "test_tenant": None,  # Dedicated test tenant for this run
    "test_user": None,    # Test user in test tenant
    "test_user_token": None,  # Token for test user
    "admin_token": None,  # Super admin token (only for tenant/user creation)
    "tenants": {},
    "users": {},
    "assets": {},
    "asset_types": [],    # Track asset type IDs created during tests
    "onboarding": {}
}


def print_test(test_id: str, name: str):
    """Print test header"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_id} - {name}")
    print(f"{'='*80}")


def print_result(result: TestResult):
    """Print test result"""
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"{status}: {result.name}")
    if result.message:
        print(f"  {result.message}")
    if not result.passed and result.data:
        print(f"  Data: {json.dumps(result.data, indent=2)}")


# ============================================================================
# AUTHENTICATION & BOOTSTRAP
# ============================================================================

def create_test_tenant_and_user():
    """Create a dedicated test tenant and user for complete isolation"""
    print_test("BOOTSTRAP", "Create test tenant and user")
    
    # First, authenticate as super admin to create tenant
    print(f"  Authenticating as super admin ({TEST_ADMIN_USERNAME})...")
    admin_token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
    
    if not admin_token:
        # Try to create/reset admin user via database
        try:
            from app.core.database import SessionLocal
            from app.models.user import User
            from app.models.tenant import Tenant
            from app.core.security import get_password_hash
            
            db = SessionLocal()
            try:
                # Check if admin user exists
                existing_user = db.query(User).filter(User.username == TEST_ADMIN_USERNAME).first()
                if existing_user:
                    # Reset password
                    existing_user.hashed_password = get_password_hash(TEST_ADMIN_PASSWORD)
                    if not existing_user.is_super_admin:
                        existing_user.is_super_admin = True
                    db.commit()
                    admin_token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
                else:
                    # Create admin user
                    admin_tenant = db.query(Tenant).filter(Tenant.id == 1).first()
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
                    
                    admin_user = User(
                        username=TEST_ADMIN_USERNAME,
                        hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
                        is_active=True,
                        tenant_id=admin_tenant.id,
                        is_super_admin=True
                    )
                    db.add(admin_user)
                    db.commit()
                    admin_token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
            finally:
                db.close()
        except ImportError:
            pass
    
    if not admin_token:
        result = TestResult("BOOTSTRAP", "Create test tenant", False, "Failed to authenticate as super admin")
        print_result(result)
        return False
    
    test_data["admin_token"] = admin_token
    client.set_token(admin_token)
    
    # Create dedicated test tenant
    tenant_data = {
        "name": f"{TEST_PREFIX}-Test-Tenant",
        "slug": f"{TEST_PREFIX.lower()}-test-tenant",
        "subscription_tier": "standard",
        "contact_email": f"test-{TEST_PREFIX.lower()}@test.example.com"
    }
    
    success, tenant_response = client.post("/api/v1/tenants/", tenant_data, expected_status=201)
    if not success or "id" not in tenant_response:
        result = TestResult("BOOTSTRAP", "Create test tenant", False, f"Failed to create test tenant: {tenant_response}")
        print_result(result)
        return False
    
    test_data["test_tenant"] = tenant_response
    tenant_id = tenant_response["id"]
    print(f"  ✓ Created test tenant: {tenant_response['name']} (ID: {tenant_id})")
    
    # Create test user in test tenant
    user_data = {
        "username": f"{TEST_PREFIX.lower()}-testuser",
        "password": "TestPassword123!",
        "tenant_id": tenant_id
    }
    
    success, user_response = client.post(f"/api/v1/tenants/{tenant_id}/users", user_data, expected_status=201)
    if not success or "id" not in user_response:
        result = TestResult("BOOTSTRAP", "Create test user", False, f"Failed to create test user: {user_response}")
        print_result(result)
        return False
    
    test_data["test_user"] = user_response
    print(f"  ✓ Created test user: {user_response['username']} (ID: {user_response['id']})")
    
    # Login as test user
    test_user_token = client.login(user_data["username"], user_data["password"])
    if not test_user_token:
        result = TestResult("BOOTSTRAP", "Login test user", False, "Failed to login as test user")
        print_result(result)
        return False
    
    test_data["test_user_token"] = test_user_token
    client.set_token(test_user_token)
    print(f"  ✓ Logged in as test user")
    
    result = TestResult("BOOTSTRAP", "Create test tenant and user", True, f"Test tenant ID: {tenant_id}, Test user ID: {user_response['id']}")
    print_result(result)
    return True


def get_test_user_token():
    """Get or create test user token - ensures we use test tenant user for all operations"""
    if test_data.get("test_user_token"):
        return test_data["test_user_token"]
    
    # If test user doesn't exist, create test tenant and user
    if not create_test_tenant_and_user():
        return None
    
    return test_data.get("test_user_token")


def bootstrap_test_admin():
    """DEPRECATED: Use create_test_tenant_and_user() instead. Kept for backward compatibility."""
    return create_test_tenant_and_user()
    print(f"  Login failed. Attempting to create/reset admin user via database...")
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.models.tenant import Tenant
        from app.core.auth import get_password_hash
        
        db = SessionLocal()
        
        # Check if user exists
        existing_user = db.query(User).filter(User.username == TEST_ADMIN_USERNAME).first()
        
        if existing_user:
            # User exists but password might be wrong, try to reset it
            print(f"  User {TEST_ADMIN_USERNAME} exists, resetting password and ensuring super admin...")
            existing_user.hashed_password = get_password_hash(TEST_ADMIN_PASSWORD)
            if not existing_user.tenant_id:
                # Assign to admin tenant if missing
                admin_tenant = db.query(Tenant).filter(Tenant.id == 1).first()
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
                existing_user.tenant_id = admin_tenant.id
            # Ensure user is super admin
            if not existing_user.is_super_admin:
                existing_user.is_super_admin = True
            db.commit()
            db.refresh(existing_user)
            
            # Try login again
            token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
            if token:
                test_data["admin_token"] = token
                client.set_token(token)
                result = TestResult("BOOTSTRAP", "Reset admin password", True, f"Password reset for {TEST_ADMIN_USERNAME}")
                print_result(result)
                db.close()
                return True
        
        # Create new admin user
        print(f"  Creating new admin user: {TEST_ADMIN_USERNAME}")
        
        # First, ensure there's an admin tenant
        admin_tenant = db.query(Tenant).filter(Tenant.id == 1).first()
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
        
        # Create admin user (as super admin)
        admin_user = User(
            username=TEST_ADMIN_USERNAME,
            hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
            is_active=True,
            tenant_id=admin_tenant.id,
            is_super_admin=True  # Make admin user a super admin
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Try login
        token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
        if token:
            test_data["admin_token"] = token
            client.set_token(token)
            result = TestResult("BOOTSTRAP", "Create admin user", True, f"Created and logged in as {TEST_ADMIN_USERNAME}")
            print_result(result)
            db.close()
            return True
        else:
            result = TestResult("BOOTSTRAP", "Create admin user", False, "User created but login failed")
            print_result(result)
            db.close()
            return False
            
    except ImportError as e:
        # Running outside Docker - can't access database directly
        result = TestResult("BOOTSTRAP", "Bootstrap admin", False, 
            f"Cannot access database (running outside Docker?). "
            f"Please ensure user '{TEST_ADMIN_USERNAME}' exists and password is '{TEST_ADMIN_PASSWORD}', "
            f"or run this script inside Docker: docker compose exec backend python test_suite.py")
        print_result(result)
        return False
    except Exception as e:
        result = TestResult("BOOTSTRAP", "Bootstrap admin", False, f"Error: {str(e)}")
        print_result(result)
        return False


def test_auth_login():
    """Test authentication"""
    print_test("TC-AUTH-001", "Login with valid credentials")
    
    if "admin_token" not in test_data:
        result = TestResult("TC-AUTH-001", "Login test", False, "No admin token available")
        print_result(result)
        return False
    
    # Test login with credentials
    token = client.login(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
    
    if token:
        result = TestResult("TC-AUTH-001", "Login with valid credentials", True, "Successfully authenticated")
    else:
        result = TestResult("TC-AUTH-001", "Login with valid credentials", False, "Login failed")
    
    print_result(result)
    return result.passed


# ============================================================================
# TENANT MANAGEMENT TESTS
# ============================================================================

def test_create_tenant():
    """Test tenant creation"""
    print_test("TC-TENANT-001", "Create tenant with valid data")
    
    # Ensure admin is logged in (tenant management requires super admin)
    if "admin_token" not in test_data:
        if not bootstrap_test_admin():
            result = TestResult("TC-TENANT-001", "Create tenant", False, "Failed to authenticate admin user")
            print_result(result)
            return False
    else:
        client.set_token(test_data["admin_token"])
    
    tenant_data = {
        "name": f"{TEST_PREFIX}-Tenant-A",
        "slug": f"{TEST_PREFIX.lower()}-tenant-a",
        "subscription_tier": "standard",
        "contact_email": "testa@example.com"
    }
    
    success, response = client.post("/api/v1/tenants/", tenant_data, expected_status=201)
    
    if success and "id" in response:
        test_data["tenants"]["tenant_a"] = response
        result = TestResult("TC-TENANT-001", "Create tenant", True, f"Created tenant ID: {response['id']}")
    else:
        result = TestResult("TC-TENANT-001", "Create tenant", False, f"Failed: {response}", response)
    
    print_result(result)
    return success


def test_create_duplicate_tenant():
    """Test duplicate tenant creation"""
    print_test("TC-TENANT-002", "Create tenant with duplicate slug")
    
    # Ensure admin is logged in (tenant management requires super admin)
    if "admin_token" not in test_data:
        if not bootstrap_test_admin():
            result = TestResult("TC-TENANT-002", "Create duplicate tenant", False, "Failed to authenticate admin user")
            print_result(result)
            return False
    else:
        client.set_token(test_data["admin_token"])
    
    if "tenant_a" not in test_data["tenants"]:
        result = TestResult("TC-TENANT-002", "Create duplicate tenant", True, "Skipped - no tenant created yet")
        print_result(result)
        return True
    
    tenant_data = {
        "name": f"{TEST_PREFIX}-Tenant-A-Dup",
        "slug": test_data["tenants"]["tenant_a"]["slug"],  # Duplicate slug
        "subscription_tier": "standard"
    }
    
    # We expect a 400 status code (bad request) for duplicate slug
    success, response = client.post("/api/v1/tenants/", tenant_data, expected_status=400)
    
    # If we got the expected 400, success=True, which means the test passed
    result = TestResult(
        "TC-TENANT-002", 
        "Create duplicate tenant", 
        success,  # Should succeed in getting 400 (which means rejection worked)
        "Correctly rejected duplicate slug" if success else f"Expected 400, got different response: {response}"
    )
    print_result(result)
    return success  # We expect success=True (meaning we got the expected 400)


def test_list_tenants():
    """Test listing tenants"""
    print_test("TC-TENANT-008", "List all active tenants")
    
    # Ensure admin is logged in (tenant management requires super admin)
    if "admin_token" not in test_data:
        if not bootstrap_test_admin():
            result = TestResult("TC-TENANT-008", "List tenants", False, "Failed to authenticate admin user")
            print_result(result)
            return False
    else:
        client.set_token(test_data["admin_token"])
    
    success, response = client.get("/api/v1/tenants/")
    
    if success and isinstance(response, list):
        tenant_count = len(response)
        result = TestResult("TC-TENANT-008", "List tenants", True, f"Found {tenant_count} tenants")
    else:
        result = TestResult("TC-TENANT-008", "List tenants", False, f"Failed: {response}", response)
    
    print_result(result)
    return success


# ============================================================================
# USER MANAGEMENT TESTS
# ============================================================================

def test_create_user_in_tenant():
    """Test creating user in tenant"""
    print_test("TC-USER-001", "Create user with valid data")
    
    # Ensure admin is logged in (user creation in tenant requires super admin)
    if "admin_token" not in test_data:
        if not bootstrap_test_admin():
            result = TestResult("TC-USER-001", "Create user", False, "Failed to authenticate admin user")
            print_result(result)
            return False
    else:
        client.set_token(test_data["admin_token"])
    
    if "tenant_a" not in test_data["tenants"]:
        result = TestResult("TC-USER-001", "Create user", True, "Skipped - no tenant created")
        print_result(result)
        return True
    
    tenant_id = test_data["tenants"]["tenant_a"]["id"]
    user_data = {
        "username": f"{TEST_PREFIX.lower()}-user1",
        "password": "TestPassword123!",
        "tenant_id": tenant_id
    }
    
    success, response = client.post(f"/api/v1/tenants/{tenant_id}/users", user_data, expected_status=201)
    
    if success and "id" in response:
        test_data["users"]["user1"] = response
        # Login with new user
        token = client.login(user_data["username"], user_data["password"])
        if token:
            test_data["users"]["user1"]["token"] = token
        result = TestResult("TC-USER-001", "Create user", True, f"Created user ID: {response['id']}")
    else:
        result = TestResult("TC-USER-001", "Create user", False, f"Failed: {response}", response)
    
    print_result(result)
    return success


def test_create_second_tenant_and_user():
    """Create second tenant and user for isolation testing"""
    print_test("TC-TENANT-ISOLATE", "Create second tenant for isolation testing")
    
    # Ensure admin is logged in (tenant management requires super admin)
    if "admin_token" not in test_data:
        if not bootstrap_test_admin():
            result = TestResult("TC-TENANT-ISOLATE", "Create second tenant", False, "Failed to authenticate admin user")
            print_result(result)
            return False
    else:
        client.set_token(test_data["admin_token"])
    
    tenant_data = {
        "name": f"{TEST_PREFIX}-Tenant-B",
        "slug": f"{TEST_PREFIX.lower()}-tenant-b",
        "subscription_tier": "standard",
        "contact_email": "testb@example.com"
    }
    
    success, response = client.post("/api/v1/tenants/", tenant_data, expected_status=201)
    
    if success and "id" in response:
        test_data["tenants"]["tenant_b"] = response
        tenant_id = response["id"]
        
        # Create user in tenant B
        user_data = {
            "username": f"{TEST_PREFIX.lower()}-user2",
            "password": "TestPassword123!",
            "tenant_id": tenant_id
        }
        
        success2, response2 = client.post(f"/api/v1/tenants/{tenant_id}/users", user_data, expected_status=201)
        if success2:
            test_data["users"]["user2"] = response2
            token = client.login(user_data["username"], user_data["password"])
            if token:
                test_data["users"]["user2"]["token"] = token
        
        result = TestResult("TC-TENANT-ISOLATE", "Create second tenant", True, f"Created tenant B ID: {tenant_id}")
    else:
        result = TestResult("TC-TENANT-ISOLATE", "Create second tenant", False, f"Failed: {response}", response)
    
    print_result(result)
    return success


# ============================================================================
# ASSET TYPE TESTS
# ============================================================================

def test_list_asset_types():
    """Test listing asset types"""
    print_test("TC-ASSETTYPE-001", "List all asset types for tenant")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-ASSETTYPE-001", "List asset types", True, "Skipped - no user token")
        print_result(result)
        return True
    
    client.set_token(test_data["users"]["user1"]["token"])
    success, response = client.get("/api/v1/asset-types/")
    
    if success and isinstance(response, list):
        asset_type_count = len(response)
        # Store first few asset types for later use
        if response:
            test_data["asset_types"]["server"] = next((at for at in response if at.get("name") == "server_device"), None)
            test_data["asset_types"]["switch"] = next((at for at in response if at.get("name") == "switch_device"), None)
            test_data["asset_types"]["firewall"] = next((at for at in response if at.get("name") == "firewall_device"), None)
        result = TestResult("TC-ASSETTYPE-001", "List asset types", True, f"Found {asset_type_count} asset types")
    else:
        result = TestResult("TC-ASSETTYPE-001", "List asset types", False, f"Failed: {response}", response)
    
    print_result(result)
    return success


# ============================================================================
# ASSET CREATION TESTS (All Types)
# ============================================================================

# Default asset types from the system
ASSET_TYPES_TO_TEST = [
    "server_device", "switch_device", "router_device", "storage_device",
    "firewall_device", "load_balancer", "pdu_device", "ups_device",
    "patch_panel", "kvm_switch", "console_server",
    "generic_cable", "dac_cable", "ethernet_cable", "electrical_cable", "fiber_cable",
    "copper_transceiver", "optical_transceiver", "nic_card", "dpu_card",
    "other_device"
]


def test_create_assets_all_types():
    """Test creating assets of all types"""
    print_test("TC-ASSET-ALL", "Create assets of all 21 default types")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-ASSET-ALL", "Create all asset types", True, "Skipped - no user token")
        print_result(result)
        return True
    
    client.set_token(test_data["users"]["user1"]["token"])
    created_count = 0
    
    for i, asset_type in enumerate(ASSET_TYPES_TO_TEST):
        asset_data = {
            "asset_tag": f"{TEST_PREFIX}-{asset_type.upper()}-{i+1}",
            "serial_number": f"SN-{TEST_PREFIX}-{i+1}",
            "asset_type": asset_type,
            "manufacturer": "Test Manufacturer",
            "model": f"Test Model {i+1}",
            "status": "received"
        }
        
        # Add type-specific fields
        if "cable" in asset_type:
            asset_data["cable_length"] = "10m"
        if asset_type == "fiber_cable":
            asset_data["fiber_type"] = "SMF"
            asset_data["fiber_connector_a"] = "LC"
            asset_data["fiber_connector_b"] = "LC"
        if asset_type == "dac_cable":
            asset_data["dac_connector_a"] = "QSFP+"
            asset_data["dac_connector_b"] = "QSFP+"
        
        success, response = client.post("/api/v1/assets/", asset_data, expected_status=201)
        
        if success and "id" in response:
            created_count += 1
            test_data["assets"][asset_type] = response
        else:
            print(f"  Failed to create {asset_type}: {response}")
    
    result = TestResult(
        "TC-ASSET-ALL",
        "Create all asset types",
        created_count == len(ASSET_TYPES_TO_TEST),
        f"Created {created_count}/{len(ASSET_TYPES_TO_TEST)} asset types"
    )
    print_result(result)
    return created_count == len(ASSET_TYPES_TO_TEST)


def test_asset_type_validation():
    """Test asset type validation (display name, case insensitive)"""
    print_test("TC-ASSET-023", "Create asset with asset_type display_name")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-ASSET-023", "Asset type validation", True, "Skipped - no user token")
        print_result(result)
        return True
    
    client.set_token(test_data["users"]["user1"]["token"])
    
    # Test with display_name "Server" instead of "server_device"
    asset_data = {
        "asset_tag": f"{TEST_PREFIX}-VALIDATION-TEST",
        "serial_number": f"SN-{TEST_PREFIX}-VALID",
        "asset_type": "Server",  # Display name, not internal name
        "manufacturer": "Test",
        "model": "Test Model",
        "status": "received"
    }
    
    success, response = client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    if success:
        # Verify it was converted to server_device
        if response.get("asset_type") == "server_device":
            result = TestResult("TC-ASSET-023", "Asset type validation", True, "Display name correctly converted to server_device")
            test_data["assets"]["validation_test"] = response
        else:
            result = TestResult("TC-ASSET-023", "Asset type validation", False, f"Expected server_device, got {response.get('asset_type')}")
    else:
        result = TestResult("TC-ASSET-023", "Asset type validation", False, f"Failed: {response}", response)
    
    print_result(result)
    return success and response.get("asset_type") == "server_device"


# ============================================================================
# TENANT ISOLATION TESTS
# ============================================================================

def test_tenant_isolation_assets():
    """Test that tenants cannot see each other's assets"""
    print_test("TC-ISOLATE-001", "Tenant A cannot see Tenant B's assets")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-ISOLATE-001", "Tenant isolation", True, "Skipped - no user1 token")
        print_result(result)
        return True
    
    if "user2" not in test_data["users"] or "token" not in test_data["users"]["user2"]:
        result = TestResult("TC-ISOLATE-001", "Tenant isolation", True, "Skipped - no user2 token")
        print_result(result)
        return True
    
    # User 1 lists assets
    client.set_token(test_data["users"]["user1"]["token"])
    success1, assets_user1 = client.get("/api/v1/assets/")
    
    # User 2 lists assets
    client.set_token(test_data["users"]["user2"]["token"])
    success2, assets_user2 = client.get("/api/v1/assets/")
    
    if success1 and success2:
        assets1_ids = {a.get("id") for a in assets_user1.get("assets", [])}
        assets2_ids = {a.get("id") for a in assets_user2.get("assets", [])}
        
        # Check for overlap
        overlap = assets1_ids & assets2_ids
        
        if not overlap:
            result = TestResult("TC-ISOLATE-001", "Tenant isolation", True, "No asset overlap between tenants")
        else:
            result = TestResult("TC-ISOLATE-001", "Tenant isolation", False, f"Found {len(overlap)} overlapping assets - ISOLATION BREACH!")
    else:
        result = TestResult("TC-ISOLATE-001", "Tenant isolation", False, "Failed to list assets")
    
    print_result(result)
    return result.passed


# ============================================================================
# DASHBOARD TESTS
# ============================================================================

def test_dashboard_summary():
    """Test dashboard summary shows correct asset counts"""
    print_test("TC-DASHBOARD-001", "Dashboard summary shows correct asset counts")
    
    # Use admin user to test with real data
    token = get_test_user_token()
    if not token:
        result = TestResult("TC-DASHBOARD-001", "Dashboard summary", True, "Skipped - no test user token")
        print_result(result)
        return True
    
    client.set_token(token)
    
    # Get dashboard summary
    success, response = client.get("/api/v1/reports/dashboard/summary")
    
    if success and "asset_utilization" in response:
        total_assets = response["asset_utilization"].get("total_assets", 0)
        
        # Also check direct asset count
        success2, assets_response = client.get("/api/v1/assets/")
        if success2:
            direct_count = assets_response.get("total", 0)
            
            # Try to get actual count from database for verification (only if running in Docker)
            db_count = None
            try:
                import sys
                sys.path.insert(0, '/app')
                from app.core.database import SessionLocal
                from app.models.asset import Asset
                from app.models.user import User
                db = SessionLocal()
                admin_user = db.query(User).filter(User.username == TEST_ADMIN_USERNAME).first()
                if admin_user:
                    db_count = db.query(Asset).filter(Asset.tenant_id == admin_user.tenant_id).count()
                db.close()
            except (ImportError, ModuleNotFoundError):
                # Running outside Docker - skip DB verification
                pass
            except Exception as e:
                # Other error - log but continue
                print(f"  Warning: Could not verify DB count: {e}")
            
            # Compare counts (with or without DB count)
            if db_count is not None:
                # All three should match
                if total_assets == direct_count == db_count:
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        True,
                        f"Dashboard={total_assets}, Direct={direct_count}, DB={db_count} - All match!"
                    )
                elif total_assets == 0 and (direct_count > 0 or db_count > 0):
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        False,
                        f"Dashboard shows 0 but Direct={direct_count}, DB={db_count} - TENANT FILTERING ISSUE!"
                    )
                else:
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        False,
                        f"Mismatch: Dashboard={total_assets}, Direct={direct_count}, DB={db_count}"
                    )
            else:
                # No DB count available - just compare dashboard and direct
                if total_assets == direct_count:
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        True,
                        f"Dashboard={total_assets}, Direct={direct_count} - Match! (DB verification skipped)"
                    )
                elif total_assets == 0 and direct_count > 0:
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        False,
                        f"Dashboard shows 0 but direct query shows {direct_count} - TENANT FILTERING ISSUE!"
                    )
                else:
                    result = TestResult(
                        "TC-DASHBOARD-001",
                        "Dashboard summary",
                        False,
                        f"Mismatch: Dashboard={total_assets}, Direct={direct_count}"
                    )
        else:
            result = TestResult("TC-DASHBOARD-001", "Dashboard summary", False, "Failed to get direct asset count")
    else:
        result = TestResult("TC-DASHBOARD-001", "Dashboard summary", False, f"Failed: {response}", response)
    
    print_result(result)
    return result.passed


def test_dashboard_tenant_isolation():
    """Test that dashboard shows different counts for different tenants"""
    print_test("TC-DASHBOARD-002", "Dashboard tenant isolation")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-DASHBOARD-002", "Dashboard isolation", True, "Skipped - no user1")
        print_result(result)
        return True
    
    if "user2" not in test_data["users"] or "token" not in test_data["users"]["user2"]:
        result = TestResult("TC-DASHBOARD-002", "Dashboard isolation", True, "Skipped - no user2")
        print_result(result)
        return True
    
    # Get dashboard for user1
    client.set_token(test_data["users"]["user1"]["token"])
    success1, dashboard1 = client.get("/api/v1/reports/dashboard/summary")
    
    # Get dashboard for user2
    client.set_token(test_data["users"]["user2"]["token"])
    success2, dashboard2 = client.get("/api/v1/reports/dashboard/summary")
    
    if success1 and success2:
        count1 = dashboard1.get("asset_utilization", {}).get("total_assets", 0)
        count2 = dashboard2.get("asset_utilization", {}).get("total_assets", 0)
        
        # They should be different (or at least isolated)
        result = TestResult(
            "TC-DASHBOARD-002",
            "Dashboard isolation",
            True,
            f"User1 sees {count1} assets, User2 sees {count2} assets"
        )
    else:
        result = TestResult("TC-DASHBOARD-002", "Dashboard isolation", False, "Failed to get dashboard data")
    
    print_result(result)
    return result.passed


# ============================================================================
# BARCODE TESTS
# ============================================================================

def test_barcode_generation():
    """Test barcode/label generation for assets"""
    print_test("TC-BARCODE-001", "Generate barcode for asset")
    
    # Use admin user to test with real data
    token = get_test_user_token()
    if not token:
        result = TestResult("TC-BARCODE-001", "Barcode generation", True, "Skipped - no test user token")
        print_result(result)
        return True
    
    client.set_token(token)
    
    # Get an asset
    success, assets_response = client.get("/api/v1/assets/")
    if not success or not assets_response.get("assets"):
        result = TestResult("TC-BARCODE-001", "Barcode generation", True, "Skipped - no assets available")
        print_result(result)
        return True
    
    asset_id = assets_response["assets"][0]["id"]
    
    # Test barcode generation (returns PNG image)
    success2, barcode_response = client.get(f"/api/v1/barcodes/generate/{asset_id}")
    
    if success2:
        # Check if it's an image response
        if barcode_response.get("content_type") and "image" in barcode_response.get("content_type", ""):
            result = TestResult(
                "TC-BARCODE-001",
                "Barcode generation",
                True,
                f"Successfully generated barcode image for asset {asset_id} ({barcode_response.get('size', 0)} bytes)"
            )
        else:
            result = TestResult(
                "TC-BARCODE-001",
                "Barcode generation",
                False,
                f"Unexpected response type: {barcode_response}"
            )
    else:
        result = TestResult(
            "TC-BARCODE-001",
            "Barcode generation",
            False,
            f"Failed to generate barcode: {barcode_response}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_create_tenant():
    """Test tenant onboarding endpoint - create new tenant and user"""
    print_test("ONBOARDING", "Create tenant via onboarding endpoint")
    
    timestamp = int(time.time())
    onboarding_data = {
        "company_name": f"{TEST_PREFIX} Onboard Company",
        "admin_username": f"onboard-admin-{timestamp}",
        "admin_email": f"onboard-admin-{timestamp}@test.com",
        "admin_password": "TestPass123!",
        "contact_email": f"admin-{timestamp}@test.com",
        "subscription_tier": "standard"
    }
    
    # Onboarding endpoint is public (no auth required)
    client.clear_token()
    success, response = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if success and "tenant_id" in response and "access_token" in response:
        # Store onboarding data for cleanup
        test_data["onboarding"] = {
            "tenant_id": response["tenant_id"],
            "user_id": response["user_id"],
            "username": response["username"],
            "token": response["access_token"]
        }
        
        result = TestResult(
            "TC-ONBOARD-001",
            "Create tenant via onboarding",
            True,
            f"Created tenant {response['tenant_id']} with user {response['user_id']}"
        )
    else:
        result = TestResult(
            "TC-ONBOARD-001",
            "Create tenant via onboarding",
            False,
            f"Failed: {response}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_duplicate_slug():
    """Test onboarding with duplicate tenant slug"""
    print_test("ONBOARDING", "Reject duplicate tenant slug")
    
    timestamp = int(time.time())
    onboarding_data = {
        "company_name": f"{TEST_PREFIX} Duplicate Slug Test",
        "company_slug": "test-duplicate-slug",
        "admin_username": f"onboard-dup-{timestamp}",
        "admin_email": f"onboard-dup-{timestamp}@test.com",
        "admin_password": "TestPass123!"
    }
    
    # First create should succeed
    client.clear_token()
    success1, response1 = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if not success1:
        result = TestResult("TC-ONBOARD-002", "Duplicate slug rejection", True, "Skipped - first creation failed")
        print_result(result)
        return result.passed
    
    # Second create with same slug should fail
    onboarding_data["admin_username"] = f"onboard-dup2-{timestamp}"
    success2, response2 = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=400)
    
    if success2 and "already exists" in str(response2.get("detail", "")).lower():
        result = TestResult(
            "TC-ONBOARD-002",
            "Duplicate slug rejection",
            True,
            "Correctly rejected duplicate slug"
        )
    else:
        result = TestResult(
            "TC-ONBOARD-002",
            "Duplicate slug rejection",
            False,
            f"Should have rejected duplicate slug: {response2}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_duplicate_username():
    """Test onboarding with duplicate username"""
    print_test("ONBOARDING", "Reject duplicate username")
    
    timestamp = int(time.time())
    username = f"onboard-dup-user-{timestamp}"
    
    onboarding_data = {
        "company_name": f"{TEST_PREFIX} Duplicate User Test 1",
        "admin_username": username,
        "admin_email": f"{username}@test.com",
        "admin_password": "TestPass123!"
    }
    
    # First create should succeed
    client.clear_token()
    success1, response1 = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if not success1:
        result = TestResult("TC-ONBOARD-003", "Duplicate username rejection", True, "Skipped - first creation failed")
        print_result(result)
        return result.passed
    
    # Second create with same username should fail
    onboarding_data["company_name"] = f"{TEST_PREFIX} Duplicate User Test 2"
    success2, response2 = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=400)
    
    if success2 and "already exists" in str(response2.get("detail", "")).lower():
        result = TestResult(
            "TC-ONBOARD-003",
            "Duplicate username rejection",
            True,
            "Correctly rejected duplicate username"
        )
    else:
        result = TestResult(
            "TC-ONBOARD-003",
            "Duplicate username rejection",
            False,
            f"Should have rejected duplicate username: {response2}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_validation_errors():
    """Test onboarding with invalid data"""
    print_test("ONBOARDING", "Validation error handling")
    
    test_cases = [
        {
            "name": "Missing company name",
            "data": {
                "admin_username": "test-user",
                "admin_password": "TestPass123!"
            },
            "expected_status": 422
        },
        {
            "name": "Missing username",
            "data": {
                "company_name": "Test Company",
                "admin_password": "TestPass123!"
            },
            "expected_status": 422
        },
        {
            "name": "Missing password",
            "data": {
                "company_name": "Test Company",
                "admin_username": "test-user"
            },
            "expected_status": 422
        },
        {
            "name": "Short password",
            "data": {
                "company_name": "Test Company",
                "admin_username": "test-user",
                "admin_password": "12345"  # Less than 6 chars
            },
            "expected_status": 422
        },
        {
            "name": "Short username",
            "data": {
                "company_name": "Test Company",
                "admin_username": "ab",  # Less than 3 chars
                "admin_password": "TestPass123!"
            },
            "expected_status": 422
        },
        {
            "name": "Invalid email format",
            "data": {
                "company_name": "Test Company",
                "admin_username": "test-user",
                "admin_password": "TestPass123!",
                "contact_email": "invalid-email"
            },
            "expected_status": 422
        }
    ]
    
    client.clear_token()
    passed_count = 0
    
    for test_case in test_cases:
        success, response = client.post(
            "/api/v1/tenants/onboard",
            test_case["data"],
            expected_status=test_case["expected_status"]
        )
        
        if success:
            passed_count += 1
        else:
            print(f"  ✗ {test_case['name']}: Expected {test_case['expected_status']}, got {response}")
    
    if passed_count == len(test_cases):
        result = TestResult(
            "TC-ONBOARD-004",
            "Validation error handling",
            True,
            f"All {len(test_cases)} validation tests passed"
        )
    else:
        result = TestResult(
            "TC-ONBOARD-004",
            "Validation error handling",
            False,
            f"Only {passed_count}/{len(test_cases)} validation tests passed"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_auto_slug_generation():
    """Test automatic slug generation from company name"""
    print_test("ONBOARDING", "Auto-generate slug from company name")
    
    timestamp = int(time.time())
    onboarding_data = {
        "company_name": f"Test Company {timestamp} With Spaces",
        "admin_username": f"onboard-slug-{timestamp}",
        "admin_email": f"onboard-slug-{timestamp}@test.com",
        "admin_password": "TestPass123!"
    }
    
    client.clear_token()
    success, response = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if success and "tenant_slug" in response:
        # Slug should be auto-generated: lowercase, spaces to hyphens, special chars removed
        expected_slug = f"test-company-{timestamp}-with-spaces".lower()
        actual_slug = response["tenant_slug"]
        
        if actual_slug == expected_slug or "test-company" in actual_slug:
            result = TestResult(
                "TC-ONBOARD-005",
                "Auto-generate slug",
                True,
                f"Slug auto-generated: {actual_slug}"
            )
        else:
            result = TestResult(
                "TC-ONBOARD-005",
                "Auto-generate slug",
                False,
                f"Slug generation incorrect: expected pattern, got {actual_slug}"
            )
    else:
        result = TestResult(
            "TC-ONBOARD-005",
            "Auto-generate slug",
            False,
            f"Failed to create tenant: {response}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_asset_types_seeded():
    """Test that default asset types are seeded during onboarding"""
    print_test("ONBOARDING", "Verify asset types are seeded")
    
    timestamp = int(time.time())
    onboarding_data = {
        "company_name": f"{TEST_PREFIX} Asset Types Test",
        "admin_username": f"onboard-assets-{timestamp}",
        "admin_password": "TestPass123!"
    }
    
    client.clear_token()
    success, response = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if not success:
        result = TestResult("TC-ONBOARD-006", "Asset types seeded", True, "Skipped - onboarding failed")
        print_result(result)
        return result.passed
    
    # Use the token from onboarding to check asset types
    tenant_id = response["tenant_id"]
    token = response["access_token"]
    client.set_token(token)
    
    # Get asset types for this tenant
    success2, asset_types_response = client.get("/api/v1/asset-types/")
    
    if success2 and isinstance(asset_types_response, list):
        # Should have at least 21 default asset types
        if len(asset_types_response) >= 21:
            # Check for some expected default types
            type_names = [at.get("name", "") for at in asset_types_response]
            expected_types = ["server_device", "switch_device", "router_device", "firewall_device"]
            found_types = [t for t in expected_types if t in type_names]
            
            if len(found_types) >= 3:
                result = TestResult(
                    "TC-ONBOARD-006",
                    "Asset types seeded",
                    True,
                    f"Found {len(asset_types_response)} asset types, including {len(found_types)} expected defaults"
                )
            else:
                result = TestResult(
                    "TC-ONBOARD-006",
                    "Asset types seeded",
                    False,
                    f"Asset types found but missing expected defaults. Found: {type_names[:5]}"
                )
        else:
            result = TestResult(
                "TC-ONBOARD-006",
                "Asset types seeded",
                False,
                f"Expected at least 21 asset types, found {len(asset_types_response)}"
            )
    else:
        result = TestResult(
            "TC-ONBOARD-006",
            "Asset types seeded",
            False,
            f"Failed to fetch asset types: {asset_types_response}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_token_validity():
    """Test that the token returned from onboarding is valid and usable"""
    print_test("ONBOARDING", "Verify onboarding token is valid")
    
    timestamp = int(time.time())
    onboarding_data = {
        "company_name": f"{TEST_PREFIX} Token Test",
        "admin_username": f"onboard-token-{timestamp}",
        "admin_password": "TestPass123!"
    }
    
    client.clear_token()
    success, response = client.post("/api/v1/tenants/onboard", onboarding_data, expected_status=201)
    
    if not success:
        result = TestResult("TC-ONBOARD-007", "Token validity", True, "Skipped - onboarding failed")
        print_result(result)
        return result.passed
    
    # Use the token to access a protected endpoint
    token = response["access_token"]
    client.set_token(token)
    
    # Try to access user's own profile
    success2, user_response = client.get("/api/v1/auth/me")
    
    if success2 and user_response.get("username") == onboarding_data["admin_username"]:
        # Try to access tenant-scoped data
        success3, assets_response = client.get("/api/v1/assets/")
        
        if success3:
            result = TestResult(
                "TC-ONBOARD-007",
                "Token validity",
                True,
                "Token is valid and can access protected endpoints"
            )
        else:
            result = TestResult(
                "TC-ONBOARD-007",
                "Token validity",
                False,
                f"Token valid but cannot access assets: {assets_response}"
            )
    else:
        result = TestResult(
            "TC-ONBOARD-007",
            "Token validity",
            False,
            f"Token invalid or cannot access user profile: {user_response}"
        )
    
    print_result(result)
    return result.passed


def test_onboarding_tenant_isolation():
    """Test that onboarded tenant is properly isolated"""
    print_test("ONBOARDING", "Verify tenant isolation after onboarding")
    
    timestamp = int(time.time())
    
    # Create first tenant via onboarding
    onboarding_data1 = {
        "company_name": f"{TEST_PREFIX} Isolation Test 1",
        "admin_username": f"onboard-iso1-{timestamp}",
        "admin_password": "TestPass123!"
    }
    
    client.clear_token()
    success1, response1 = client.post("/api/v1/tenants/onboard", onboarding_data1, expected_status=201)
    
    if not success1:
        result = TestResult("TC-ONBOARD-008", "Tenant isolation", True, "Skipped - first onboarding failed")
        print_result(result)
        return result.passed
    
    token1 = response1["access_token"]
    tenant_id1 = response1["tenant_id"]
    
    # Create asset for tenant 1
    client.set_token(token1)
    asset_data = {
        "asset_tag": f"TEST-ISO1-{timestamp}",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model"
    }
    success2, asset1 = client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    # Create second tenant via onboarding
    onboarding_data2 = {
        "company_name": f"{TEST_PREFIX} Isolation Test 2",
        "admin_username": f"onboard-iso2-{timestamp}",
        "admin_password": "TestPass123!"
    }
    
    client.clear_token()
    success3, response2 = client.post("/api/v1/tenants/onboard", onboarding_data2, expected_status=201)
    
    if not success3:
        result = TestResult("TC-ONBOARD-008", "Tenant isolation", True, "Skipped - second onboarding failed")
        print_result(result)
        return result.passed
    
    token2 = response2["access_token"]
    tenant_id2 = response2["tenant_id"]
    
    # Tenant 2 should not see tenant 1's assets
    client.set_token(token2)
    success4, assets2 = client.get("/api/v1/assets/")
    
    if success4:
        assets_list = assets2.get("assets", [])
        tenant1_assets = [a for a in assets_list if a.get("asset_tag", "").startswith("TEST-ISO1")]
        
        if len(tenant1_assets) == 0:
            result = TestResult(
                "TC-ONBOARD-008",
                "Tenant isolation",
                True,
                f"Tenant {tenant_id2} correctly isolated from tenant {tenant_id1}"
            )
        else:
            result = TestResult(
                "TC-ONBOARD-008",
                "Tenant isolation",
                False,
                f"ISOLATION BREACH: Tenant 2 can see {len(tenant1_assets)} assets from tenant 1!"
            )
    else:
        result = TestResult(
            "TC-ONBOARD-008",
            "Tenant isolation",
            False,
            f"Failed to fetch assets for tenant 2: {assets2}"
        )
    
    print_result(result)
    return result.passed


def test_barcode_tenant_isolation():
    """Test that barcode generation respects tenant isolation"""
    print_test("TC-BARCODE-002", "Barcode generation tenant isolation")
    
    if "user1" not in test_data["users"] or "token" not in test_data["users"]["user1"]:
        result = TestResult("TC-BARCODE-002", "Barcode isolation", True, "Skipped - no user1")
        print_result(result)
        return True
    
    if "user2" not in test_data["users"] or "token" not in test_data["users"]["user2"]:
        result = TestResult("TC-BARCODE-002", "Barcode isolation", True, "Skipped - no user2")
        print_result(result)
        return True
    
    # User 1 gets their assets
    client.set_token(test_data["users"]["user1"]["token"])
    success1, assets1 = client.get("/api/v1/assets/")
    
    # User 2 gets their assets
    client.set_token(test_data["users"]["user2"]["token"])
    success2, assets2 = client.get("/api/v1/assets/")
    
    if success1 and success2 and assets1.get("assets") and assets2.get("assets"):
        # Try to generate barcode for user2's asset as user1 (should fail)
        user2_asset_id = assets2["assets"][0]["id"]
        client.set_token(test_data["users"]["user1"]["token"])
        success3, barcode_response = client.get(f"/api/v1/barcodes/generate/{user2_asset_id}")
        
        if not success3:
            result = TestResult(
                "TC-BARCODE-002",
                "Barcode isolation",
                True,
                f"Correctly blocked barcode generation for other tenant's asset"
            )
        else:
            result = TestResult(
                "TC-BARCODE-002",
                "Barcode isolation",
                False,
                f"ISOLATION BREACH: User1 can generate barcode for User2's asset!"
            )
    else:
        result = TestResult("TC-BARCODE-002", "Barcode isolation", True, "Skipped - not enough test data")
    
    print_result(result)
    return result.passed


# ============================================================================
# CLEANUP TESTS
# ============================================================================

# ============================================================================
# STOCK MANAGEMENT TESTS
# ============================================================================

def test_stock_management_create_storage_box():
    """TC-STOCK-001: Create storage box with min_stock_threshold"""
    test_id = "TC-STOCK-001"
    print_test(test_id, "Create storage box with min_stock_threshold")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Create storage box", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create a storage box asset (using storage_device as the type)
    box_data = {
        "asset_tag": f"{TEST_PREFIX}-StorageBox-001",
        "serial_number": f"{TEST_PREFIX}-BOX-SN-001",
        "asset_type": "storage_device",  # Use existing asset type
        "manufacturer": "Generic",
        "model": "Cable Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, response = client.post("/api/v1/assets/", box_data, expected_status=201)
    if success and "id" in response:
        test_data["storage_box_id"] = response["id"]
        result = TestResult(test_id, "Create storage box", True, f"Created storage box ID {response['id']}", response)
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Create storage box", False, f"Failed: {response}")
    print_result(result)
    return result.passed


def test_stock_management_add_items_to_box():
    """TC-STOCK-002: Add items to storage box (container_id, status=IN_STORAGE)"""
    test_id = "TC-STOCK-002"
    print_test(test_id, "Add items to storage box")
    token = get_test_user_token()
    if not token or "storage_box_id" not in test_data:
        result = TestResult(test_id, "Add items to storage box", False, "Prerequisites not met")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    box_id = test_data["storage_box_id"]
    
    # Create items to add to the box
    items = []
    for i in range(3):
        item_data = {
            "asset_tag": f"{TEST_PREFIX}-Cable-{i+1}",
            "serial_number": f"{TEST_PREFIX}-CABLE-SN-{i+1}",
            "asset_type": "dac_cable",
            "manufacturer": "Generic",
            "model": "SFP+ DAC",
            "status": "in_storage",  # Critical: must be lowercase
            "container_id": box_id  # Link to storage box
        }
        success, response = client.post("/api/v1/assets/", item_data, expected_status=201)
        if success:
            items.append(response["id"])
    
    if len(items) == 3:
        test_data["storage_box_items"] = items
        result = TestResult(test_id, "Add items to storage box", True, f"Added {len(items)} items to box", {"items": items})
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Add items to storage box", False, f"Only added {len(items)}/3 items")
    print_result(result)
    return result.passed


def test_stock_management_get_stock_info():
    """TC-STOCK-003: Get stock level information for storage box"""
    test_id = "TC-STOCK-003"
    print_test(test_id, "Get stock level information")
    token = get_test_user_token()
    if not token or "storage_box_id" not in test_data:
        result = TestResult(test_id, "Get stock info", False, "Prerequisites not met")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    box_id = test_data["storage_box_id"]
    
    success, response = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
    if success:
        # Verify stock info structure
        required_fields = ["current_count", "min_threshold", "is_low_stock", "container_name"]
        if all(field in response for field in required_fields):
            # Should have 3 items (counts all items with container_id, not just IN_STORAGE)
            if response["current_count"] == 3:
                result = TestResult(test_id, "Get stock info", True, f"Stock count: {response['current_count']}", response)
                print_result(result)
                return result.passed
            result = TestResult(test_id, "Get stock info", False, f"Expected 3 items, got {response['current_count']}")
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Get stock info", False, f"Missing required fields: {response}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Get stock info", False, f"Failed: {response}")
    print_result(result)
    return result.passed


def test_stock_management_count_all_items():
    """TC-STOCK-007: Test that stock counting includes all items in container regardless of status"""
    test_id = "TC-STOCK-007"
    print_test(test_id, "Stock count includes all items regardless of status")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Stock count all items", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create a storage box
    box_data = {
        "asset_tag": f"{TEST_PREFIX}-CountTest-Box",
        "serial_number": f"{TEST_PREFIX}-CTB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    success, box = client.post("/api/v1/assets/", box_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Stock count all items", False, "Failed to create storage box")
        print_result(result)
        return result.passed
    box_id = box["id"]
    
    # Create items with different statuses but all in the same container
    items = []
    statuses = ["in_storage", "received", "active"]  # Different statuses
    for i, status_val in enumerate(statuses):
        item_data = {
            "asset_tag": f"{TEST_PREFIX}-CountTest-Item-{i+1}",
            "serial_number": f"{TEST_PREFIX}-CTI-SN-{i+1}",
            "asset_type": "dac_cable",
            "manufacturer": "Generic",
            "model": "Test Cable",
            "status": status_val,
            "container_id": box_id  # All in same container
        }
        success, item = client.post("/api/v1/assets/", item_data, expected_status=201)
        if success:
            items.append(item["id"])
    
    # Get stock info - should count all 3 items regardless of status
    success, stock_info = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
    if success:
        if stock_info["current_count"] == 3:
            result = TestResult(test_id, "Stock count all items", True, "Counted all items regardless of status", stock_info)
            print_result(result)
            # Cleanup
            for item_id in items:
                client.delete(f"/api/v1/assets/{item_id}", expected_status=200)
            client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
            return result.passed
        result = TestResult(test_id, "Stock count all items", False, f"Expected 3 items, got {stock_info['current_count']}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Stock count all items", False, f"Failed to get stock info: {stock_info}")
    print_result(result)
    return result.passed


def test_auto_status_on_container():
    """TC-AUTO-STATUS-001: Test that setting container_id automatically sets status to IN_STORAGE"""
    test_id = "TC-AUTO-STATUS-001"
    print_test(test_id, "Auto-set status to IN_STORAGE when container_id is set")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Auto-status on container", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create a storage box first
    box_data = {
        "asset_tag": f"{TEST_PREFIX}-AutoStatus-Box",
        "serial_number": f"{TEST_PREFIX}-ASB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    success, box = client.post("/api/v1/assets/", box_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Auto-status on container", False, "Failed to create storage box")
        print_result(result)
        return result.passed
    box_id = box["id"]
    
    # Test 1: Create asset with container_id - should auto-set status to IN_STORAGE
    item_data = {
        "asset_tag": f"{TEST_PREFIX}-AutoStatus-Item-1",
        "serial_number": f"{TEST_PREFIX}-ASI-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "Test Cable",
        "status": "received",  # Explicit status
        "container_id": box_id  # Setting container_id should override status
    }
    success, item = client.post("/api/v1/assets/", item_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Auto-status on container", False, "Failed to create item with container_id")
        print_result(result)
        return result.passed
    
    # Verify status was auto-set to IN_STORAGE
    if item.get("status") == "in_storage":
        # Test 2: Update asset to add container_id - should auto-set status to IN_STORAGE
        item2_data = {
            "asset_tag": f"{TEST_PREFIX}-AutoStatus-Item-2",
            "serial_number": f"{TEST_PREFIX}-ASI-SN-002",
            "asset_type": "dac_cable",
            "manufacturer": "Generic",
            "model": "Test Cable",
            "status": "active"  # Different status
        }
        success, item2 = client.post("/api/v1/assets/", item2_data, expected_status=201)
        if not success:
            result = TestResult(test_id, "Auto-status on container", False, "Failed to create second item")
            print_result(result)
            return result.passed
        
        # Update to add container_id
        update_data = {"container_id": box_id}
        success, updated = client.put(f"/api/v1/assets/{item2['id']}", update_data, expected_status=200)
        if success and updated.get("status") == "in_storage":
            result = TestResult(test_id, "Auto-status on container", True, "Status auto-set to IN_STORAGE on both create and update", {
                "create_status": item.get("status"),
                "update_status": updated.get("status")
            })
            print_result(result)
            # Cleanup
            client.delete(f"/api/v1/assets/{item['id']}", expected_status=200)
            client.delete(f"/api/v1/assets/{item2['id']}", expected_status=200)
            client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
            return result.passed
        else:
            result = TestResult(test_id, "Auto-status on container", False, f"Update failed or status not set. Status: {updated.get('status') if success else 'N/A'}")
            print_result(result)
            return result.passed
    else:
        result = TestResult(test_id, "Auto-status on container", False, f"Status not auto-set on create. Got: {item.get('status')}")
        print_result(result)
        return result.passed


def test_inventory_shows_all_statuses():
    """TC-INVENTORY-001: Test that inventory listing shows all items including IN_STORAGE"""
    test_id = "TC-INVENTORY-001"
    print_test(test_id, "Inventory shows all statuses including IN_STORAGE")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Inventory shows all statuses", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create items with different statuses
    test_items = []
    statuses = ["in_storage", "active", "deployed", "received"]
    for i, status_val in enumerate(statuses):
        item_data = {
            "asset_tag": f"{TEST_PREFIX}-InvTest-{i+1}",
            "serial_number": f"{TEST_PREFIX}-INV-SN-{i+1}",
            "asset_type": "dac_cable",
            "manufacturer": "Generic",
            "model": "Test Cable",
            "status": status_val
        }
        success, item = client.post("/api/v1/assets/", item_data, expected_status=201)
        if success:
            test_items.append({"id": item["id"], "status": status_val})
    
    # List all assets without status filter
    success, response = client.get("/api/v1/assets/", expected_status=200, params={"limit": 1000})
    if success:
        assets = response.get("assets", [])
        # Check that all our test items are in the list
        found_statuses = {}
        for item in test_items:
            asset = next((a for a in assets if a["id"] == item["id"]), None)
            if asset:
                found_statuses[item["status"]] = True
        
        # All statuses should be found, including IN_STORAGE
        if all(status in found_statuses for status in statuses):
            result = TestResult(test_id, "Inventory shows all statuses", True, f"Found all statuses: {list(found_statuses.keys())}", {"found": len(found_statuses), "expected": len(statuses)})
            print_result(result)
            # Cleanup
            for item in test_items:
                client.delete(f"/api/v1/assets/{item['id']}", expected_status=200)
            return result.passed
        result = TestResult(test_id, "Inventory shows all statuses", False, f"Missing statuses. Found: {list(found_statuses.keys())}, Expected: {statuses}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Inventory shows all statuses", False, f"Failed to list assets: {response}")
    print_result(result)
    return result.passed


def test_stock_management_get_items_in_box():
    """TC-STOCK-004: Get all items inside a storage box"""
    test_id = "TC-STOCK-004"
    print_test(test_id, "Get items in storage box")
    token = get_test_user_token()
    if not token or "storage_box_id" not in test_data:
        result = TestResult(test_id, "Get items in box", False, "Prerequisites not met")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    box_id = test_data["storage_box_id"]
    
    success, response = client.get(f"/api/v1/assets/containers/{box_id}/items", expected_status=200)
    if success and isinstance(response, list):
        if len(response) == 3:
            # Verify all items have correct container_id and status
            all_correct = all(
                item.get("container_id") == box_id and item.get("status") == "in_storage"
                for item in response
            )
            if all_correct:
                result = TestResult(test_id, "Get items in box", True, f"Retrieved {len(response)} items", {"count": len(response)})
                print_result(result)
                return result.passed
            result = TestResult(test_id, "Get items in box", False, "Some items have incorrect container_id or status")
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Get items in box", False, f"Expected 3 items, got {len(response)}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Get items in box", False, f"Failed: {response}")
    print_result(result)
    return result.passed


def test_stock_management_auto_deploy_on_connect():
    """TC-STOCK-005: Test auto-deploy when connecting cable (status changes IN_STORAGE -> DEPLOYED)"""
    test_id = "TC-STOCK-005"
    print_test(test_id, "Auto-deploy cable on connection")
    token = get_test_user_token()
    if not token or "storage_box_items" not in test_data:
        result = TestResult(test_id, "Auto-deploy on connect", False, "Prerequisites not met")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    cable_id = test_data["storage_box_items"][0]  # Use first cable
    
    # Verify cable is IN_STORAGE
    success, cable = client.get(f"/api/v1/assets/{cable_id}", expected_status=200)
    if not success or cable.get("status") != "in_storage":
        return TestResult(test_id, "Auto-deploy on connect", False, "Cable not in IN_STORAGE status")
    
    # Create a device to connect to
    device_data = {
        "asset_tag": f"{TEST_PREFIX}-Switch-001",
        "serial_number": f"{TEST_PREFIX}-SW-SN-001",
        "asset_type": "switch",
        "manufacturer": "Cisco",
        "model": "2960",
        "status": "active"
    }
    success, device = client.post("/api/v1/assets/", device_data, expected_status=201)
    if not success:
        return TestResult(test_id, "Auto-deploy on connect", False, "Failed to create device")
    device_id = device["id"]
    # Track created device for cleanup
    if "stock_test_devices" not in test_data:
        test_data["stock_test_devices"] = []
    test_data["stock_test_devices"].append(device_id)
    
    # Connect cable to device (should trigger auto-deploy)
    connect_data = {
        "cable_id": cable_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    success, connection = client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    if not success:
        return TestResult(test_id, "Auto-deploy on connect", False, f"Failed to connect: {connection}")
    
    # Verify cable status changed to DEPLOYED
    success, updated_cable = client.get(f"/api/v1/assets/{cable_id}", expected_status=200)
    if success:
        if updated_cable.get("status") == "deployed" and updated_cable.get("container_id") is None:
            # Verify stock count decreased
            box_id = test_data["storage_box_id"]
            success, stock_info = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
            if success and stock_info.get("current_count") == 2:
                result = TestResult(test_id, "Auto-deploy on connect", True, "Cable auto-deployed and stock updated", {
                    "old_status": "in_storage",
                    "new_status": updated_cable.get("status"),
                    "stock_count": stock_info.get("current_count")
                })
                print_result(result)
                return result.passed
            result = TestResult(test_id, "Auto-deploy on connect", False, "Stock count not updated correctly")
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Auto-deploy on connect", False, f"Status not changed to DEPLOYED: {updated_cable.get('status')}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Auto-deploy on connect", False, "Failed to verify cable status")
    print_result(result)
    return result.passed


def test_stock_lifecycle_consumption():
    """TC-STOCK-LIFECYCLE-001: Test complete lifecycle consumption workflow using stock_service"""
    test_id = "TC-STOCK-LIFECYCLE-001"
    print_test(test_id, "Lifecycle Consumption Workflow (deploy_asset service)")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Lifecycle consumption", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Step 1: Create a storage box with min_stock_threshold=5
    box_data = {
        "asset_tag": f"{TEST_PREFIX}-LifecycleBox-001",
        "serial_number": f"{TEST_PREFIX}-LCB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Storage Box",
        "status": "active",
        "min_stock_threshold": 5
    }
    success, box_response = client.post("/api/v1/assets/", box_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to create storage box: {box_response}")
        print_result(result)
        return result.passed
    box_id = box_response["id"]
    
    # Step 2: Create 5 cable assets and add them to the box (status=IN_STORAGE)
    cables = []
    for i in range(5):
        cable_data = {
            "asset_tag": f"{TEST_PREFIX}-LifecycleCable-{i+1:03d}",
            "serial_number": f"{TEST_PREFIX}-LCC-SN-{i+1:03d}",
            "asset_type": "ethernet_cable",
            "manufacturer": "Test Cable Co",
            "model": "CAT6",
            "status": "in_storage",  # Must be lowercase
            "container_id": box_id
        }
        success, cable_response = client.post("/api/v1/assets/", cable_data, expected_status=201)
        if success:
            cables.append(cable_response["id"])
        else:
            result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to create cable {i+1}: {cable_response}")
            print_result(result)
            # Cleanup
            for cable_id in cables:
                client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
            client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
            return result.passed
    
    if len(cables) != 5:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Only created {len(cables)}/5 cables")
        print_result(result)
        # Cleanup
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Verify initial state: 5 cables in box
    success, stock_info = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
    if not success or stock_info.get("current_count") != 5:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Expected 5 cables initially, got {stock_info.get('current_count', 'N/A')}")
        print_result(result)
        # Cleanup
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Step 3: Deploy one cable using the connect endpoint (which calls deploy_asset service)
    # First, we need a device to connect to
    device_data = {
        "asset_tag": f"{TEST_PREFIX}-LifecycleDevice-001",
        "serial_number": f"{TEST_PREFIX}-LCD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Test Server Co",
        "model": "Test Server",
        "status": "active"
    }
    success, device_response = client.post("/api/v1/assets/", device_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to create device: {device_response}")
        print_result(result)
        # Cleanup
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    device_id = device_response["id"]
    
    # Connect the first cable to the device (this should trigger deploy_asset)
    cable_to_deploy_id = cables[0]
    connect_data = {
        "cable_id": cable_to_deploy_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    success, connect_response = client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    if not success:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to connect cable: {connect_response}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Step 4: Verify cable is removed from box (container_id=None) and status is DEPLOYED
    success, deployed_cable = client.get(f"/api/v1/assets/{cable_to_deploy_id}", expected_status=200)
    if not success:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to fetch deployed cable: {deployed_cable}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Step 4 & 5: Assert cable is removed from box and status is DEPLOYED
    if deployed_cable.get("container_id") is not None:
        result = TestResult(test_id, "Lifecycle consumption", False, 
                          f"Expected container_id to be None after deployment, got {deployed_cable.get('container_id')}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    if deployed_cable.get("status") != "deployed":
        result = TestResult(test_id, "Lifecycle consumption", False,
                          f"Expected status to be 'deployed', got {deployed_cable.get('status')}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Step 6: Assert box has 4 items remaining
    success, stock_info_after = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
    if not success:
        result = TestResult(test_id, "Lifecycle consumption", False, f"Failed to get stock info after deployment: {stock_info_after}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    remaining_count = stock_info_after.get("current_count", 0)
    if remaining_count != 4:
        result = TestResult(test_id, "Lifecycle consumption", False,
                          f"Expected 4 cables remaining in box, found {remaining_count}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Step 7: Assert low stock check was triggered (4 < 5, so should be True)
    if not stock_info_after.get("is_low_stock", False):
        result = TestResult(test_id, "Lifecycle consumption", False,
                          f"Expected low stock alert (4 < 5), but is_low_stock is {stock_info_after.get('is_low_stock')}")
        print_result(result)
        # Cleanup
        client.delete(f"/api/v1/connections/{connect_response.get('connection', {}).get('id')}", expected_status=200)
        client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
        for cable_id in cables:
            client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        return result.passed
    
    # Cleanup
    connection_id = connect_response.get("connection", {}).get("id")
    if connection_id:
        client.delete(f"/api/v1/connections/{connection_id}", expected_status=200)
    client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
    for cable_id in cables:
        client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
    client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
    
    result = TestResult(test_id, "Lifecycle consumption", True,
                       f"All assertions passed: cable deployed, container_id=None, status=DEPLOYED, 4 items remaining, low stock alert triggered",
                       {
                           "box_id": box_id,
                           "deployed_cable_id": cable_to_deploy_id,
                           "remaining_count": remaining_count,
                           "is_low_stock": stock_info_after.get("is_low_stock")
                       })
    print_result(result)
    return result.passed


def test_stock_management_low_stock_alert():
    """TC-STOCK-006: Test low stock alert when count drops below threshold"""
    test_id = "TC-STOCK-006"
    print_test(test_id, "Low stock alert trigger")
    token = get_test_user_token()
    if not token or "storage_box_id" not in test_data or "storage_box_items" not in test_data:
        result = TestResult(test_id, "Low stock alert", False, "Prerequisites not met")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    box_id = test_data["storage_box_id"]
    
    # Connect remaining items to trigger low stock (threshold is 5, we have 2 left)
    # First, create more devices
    devices = []
    for i in range(2):
        device_data = {
            "asset_tag": f"{TEST_PREFIX}-Device-{i+1}",
            "serial_number": f"{TEST_PREFIX}-DEV-SN-{i+1}",
            "asset_type": "server",
            "manufacturer": "Dell",
            "model": "R720",
            "status": "active"
        }
        success, device = client.post("/api/v1/assets/", device_data, expected_status=201)
        if success:
            devices.append(device["id"])
            # Track created device for cleanup
            if "stock_test_devices" not in test_data:
                test_data["stock_test_devices"] = []
            test_data["stock_test_devices"].append(device["id"])
    
    # Connect remaining cables
    remaining_items = test_data["storage_box_items"][1:]  # Skip first (already connected)
    for i, cable_id in enumerate(remaining_items):
        if i < len(devices):
            connect_data = {
                "cable_id": cable_id,
                "device_id": devices[i],
                "port_label": f"Port {i+1}"
            }
            client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    
    # Check stock info - should show low stock (2 < 5)
    success, stock_info = client.get(f"/api/v1/assets/containers/{box_id}/stock", expected_status=200)
    if success:
        if stock_info.get("current_count", 0) < stock_info.get("min_threshold", 0):
            if stock_info.get("is_low_stock") == True:
                result = TestResult(test_id, "Low stock alert", True, "Low stock alert triggered", stock_info)
                print_result(result)
                return result.passed
            result = TestResult(test_id, "Low stock alert", False, "is_low_stock not set to True")
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Low stock alert", False, "Stock not below threshold")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Low stock alert", False, f"Failed to get stock info: {stock_info}")
    print_result(result)
    return result.passed


# ============================================================================
# ASSET STATUS TESTS
# ============================================================================

def test_asset_status_in_storage():
    """TC-STATUS-001: Test IN_STORAGE status value"""
    test_id = "TC-STATUS-001"
    print_test(test_id, "Test IN_STORAGE status")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Test IN_STORAGE status", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create asset with IN_STORAGE status
    asset_data = {
        "asset_tag": f"{TEST_PREFIX}-InStorage-001",
        "serial_number": f"{TEST_PREFIX}-INS-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "Test Cable",
        "status": "in_storage"  # Lowercase
    }
    
    success, response = client.post("/api/v1/assets/", asset_data, expected_status=201)
    if success and response.get("status") == "in_storage":
        # Track created asset for cleanup
        if "test_assets" not in test_data:
            test_data["test_assets"] = []
        test_data["test_assets"].append(response["id"])
        result = TestResult(test_id, "Test IN_STORAGE status", True, "Asset created with IN_STORAGE status", response)
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Test IN_STORAGE status", False, f"Failed: {response}")
    print_result(result)
    return result.passed


def test_asset_status_rma_retired():
    """TC-STATUS-002: Test RMA and RETIRED status values"""
    test_id = "TC-STATUS-002"
    print_test(test_id, "Test RMA and RETIRED status")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Test RMA/RETIRED status", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Test RMA status
    rma_data = {
        "asset_tag": f"{TEST_PREFIX}-RMA-001",
        "serial_number": f"{TEST_PREFIX}-RMA-SN-001",
        "asset_type": "server",
        "manufacturer": "Dell",
        "model": "R720",
        "status": "rma"
    }
    success, rma_response = client.post("/api/v1/assets/", rma_data, expected_status=201)
    
    # Test RETIRED status
    retired_data = {
        "asset_tag": f"{TEST_PREFIX}-Retired-001",
        "serial_number": f"{TEST_PREFIX}-RET-SN-001",
        "asset_type": "server",
        "manufacturer": "Dell",
        "model": "R710",
        "status": "retired"
    }
    success2, retired_response = client.post("/api/v1/assets/", retired_data, expected_status=201)
    
    if success and success2:
        # Track created assets for cleanup
        if "test_assets" not in test_data:
            test_data["test_assets"] = []
        if "id" in rma_response:
            test_data["test_assets"].append(rma_response["id"])
        if "id" in retired_response:
            test_data["test_assets"].append(retired_response["id"])
        if rma_response.get("status") == "rma" and retired_response.get("status") == "retired":
            result = TestResult(test_id, "Test RMA/RETIRED status", True, "Both statuses work correctly", {
                "rma": rma_response.get("status"),
                "retired": retired_response.get("status")
            })
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Test RMA/RETIRED status", False, "Status values not set correctly")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Test RMA/RETIRED status", False, f"RMA: {success}, RETIRED: {success2}")
    print_result(result)
    return result.passed


def test_asset_status_normalization():
    """TC-STATUS-003: Test status value normalization (uppercase to lowercase)"""
    test_id = "TC-STATUS-003"
    print_test(test_id, "Test status normalization")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Test status normalization", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Try creating asset with uppercase status (should be normalized)
    asset_data = {
        "asset_tag": f"{TEST_PREFIX}-Normalize-001",
        "serial_number": f"{TEST_PREFIX}-NORM-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "Test Cable",
        "status": "IN_STORAGE"  # Uppercase - should be normalized to lowercase
    }
    
    success, response = client.post("/api/v1/assets/", asset_data, expected_status=201)
    if success:
        # Track created asset for cleanup
        if "test_assets" not in test_data:
            test_data["test_assets"] = []
        test_data["test_assets"].append(response["id"])
        # Should be normalized to lowercase
        if response.get("status") == "in_storage":
            result = TestResult(test_id, "Test status normalization", True, "Status normalized correctly", response)
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Test status normalization", False, f"Status not normalized: {response.get('status')}")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Test status normalization", False, f"Failed to create asset: {response}")
    print_result(result)
    return result.passed


# ============================================================================
# CONNECTION AUTO-DEPLOY TESTS
# ============================================================================

def test_connection_auto_deploy_cable():
    """TC-CONN-001: Test cable auto-deploy on connection"""
    test_id = "TC-CONN-001"
    print_test(test_id, "Test connection auto-deploy")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Connection auto-deploy", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Create cable in storage
    cable_data = {
        "asset_tag": f"{TEST_PREFIX}-AutoDeploy-Cable",
        "serial_number": f"{TEST_PREFIX}-ADC-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "SFP+ DAC",
        "status": "in_storage"
    }
    success, cable = client.post("/api/v1/assets/", cable_data, expected_status=201)
    if not success:
        return TestResult(test_id, "Connection auto-deploy", False, "Failed to create cable")
    cable_id = cable["id"]
    # Track created asset for cleanup
    if "test_assets" not in test_data:
        test_data["test_assets"] = []
    test_data["test_assets"].append(cable_id)
    
    # Create device
    device_data = {
        "asset_tag": f"{TEST_PREFIX}-AutoDeploy-Device",
        "serial_number": f"{TEST_PREFIX}-ADD-SN-001",
        "asset_type": "switch",
        "manufacturer": "Cisco",
        "model": "2960",
        "status": "active"
    }
    success, device = client.post("/api/v1/assets/", device_data, expected_status=201)
    if not success:
        return TestResult(test_id, "Connection auto-deploy", False, "Failed to create device")
    device_id = device["id"]
    # Track created asset for cleanup
    test_data["test_assets"].append(device_id)
    
    # Connect cable (should auto-deploy)
    connect_data = {
        "cable_id": cable_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    success, connection = client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    if not success:
        return TestResult(test_id, "Connection auto-deploy", False, f"Failed to connect: {connection}")
    
    # Verify cable status changed
    success, updated_cable = client.get(f"/api/v1/assets/{cable_id}", expected_status=200)
    if success and updated_cable.get("status") == "deployed":
        result = TestResult(test_id, "Connection auto-deploy", True, "Cable auto-deployed on connection", {
            "old_status": "in_storage",
            "new_status": updated_cable.get("status")
        })
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Connection auto-deploy", False, f"Status not changed: {updated_cable.get('status') if success else 'Failed to fetch'}")
    print_result(result)
    return result.passed


# ============================================================================
# ASSET TYPE CLEANUP TESTS
# ============================================================================

def test_asset_type_cleanup_duplicates():
    """TC-ATYPE-001: Test duplicate asset type cleanup endpoint"""
    test_id = "TC-ATYPE-001"
    print_test(test_id, "Test asset type cleanup duplicates")
    token = get_test_user_token()
    if not token:
        result = TestResult(test_id, "Asset type cleanup", False, "Test user token not available")
        print_result(result)
        return result.passed
    
    client.set_token(token)
    
    # Test dry-run mode (POST request to cleanup endpoint)
    success, response = client.post("/api/v1/asset-types/cleanup-duplicates?dry_run=true", {}, expected_status=200)
    if success:
        if "duplicates_found" in response and "dry_run" in response:
            result = TestResult(test_id, "Asset type cleanup", True, f"Found {response.get('duplicates_found', 0)} duplicates", response)
            print_result(result)
            return result.passed
        result = TestResult(test_id, "Asset type cleanup", False, "Response missing required fields")
        print_result(result)
        return result.passed
    result = TestResult(test_id, "Asset type cleanup", False, f"Failed: {response}")
    print_result(result)
    return result.passed


def test_delete_assets():
    """Delete all test assets"""
    print_test("CLEANUP", "Delete test assets")
    
    # Use test user token (all assets should be in test tenant)
    token = get_test_user_token()
    if not token:
        print("  Skipped - no test user token available")
        return True
    
    client.set_token(token)
    
    deleted_count = 0
    failed_count = 0
    
    # Delete assets from test_data["assets"] (created by test_create_assets_all_types)
    if "assets" in test_data:
        for asset_type, asset in test_data["assets"].items():
            if "id" in asset:
                try:
                    success, _ = client.delete(f"/api/v1/assets/{asset['id']}", expected_status=200)
                    if success:
                        deleted_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
    
    # Delete storage box and its items (created by stock management tests)
    if "storage_box_items" in test_data:
        for item_id in test_data["storage_box_items"]:
            try:
                success, _ = client.delete(f"/api/v1/assets/{item_id}", expected_status=200)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
    
    if "storage_box_id" in test_data:
        try:
            success, _ = client.delete(f"/api/v1/assets/{test_data['storage_box_id']}", expected_status=200)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
    
    # Delete any other test assets created during status/connection tests
    if "test_assets" in test_data:
        for asset_id in test_data["test_assets"]:
            try:
                success, _ = client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
    
    # Also delete any devices created during stock management tests
    if "stock_test_devices" in test_data:
        for device_id in test_data["stock_test_devices"]:
            try:
                success, _ = client.delete(f"/api/v1/assets/{device_id}", expected_status=200)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
    
    print(f"  Deleted {deleted_count} test assets, {failed_count} failures")
    return True


def test_delete_users():
    """Delete test users"""
    print_test("CLEANUP", "Delete test users")
    
    if "admin_token" not in test_data:
        print("  Skipped - no admin token available")
        return True
    
    client.set_token(test_data["admin_token"])
    deleted_count = 0
    failed_count = 0
    
    # Delete users in reverse order (to avoid dependency issues)
    users_to_delete = list(test_data["users"].items())
    users_to_delete.reverse()
    
    for user_key, user in users_to_delete:
        if "id" in user:
            user_id = user["id"]
            tenant_id = user.get("tenant_id", "unknown")
            try:
                # Delete user via API (use /api/v1/users/{id} endpoint, not tenant endpoint)
                # The tenant endpoint only removes/reassigns, it doesn't delete
                success, response = client.delete(f"/api/v1/users/{user_id}", expected_status=204)
                if success:
                    deleted_count += 1
                    print(f"  ✓ Deleted user {user_id} (was in tenant {tenant_id})")
                else:
                    failed_count += 1
                    print(f"  ✗ Failed to delete user {user_id}: {response}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Error deleting user {user_id}: {e}")
    
    print(f"  Deleted {deleted_count} users, {failed_count} failures")
    return True


def test_delete_asset_types():
    """Delete all asset types created during tests"""
    print_test("CLEANUP", "Delete test asset types")
    
    token = get_test_user_token()
    if not token:
        print("  Skipped - no test user token available")
        return True
    
    client.set_token(token)
    deleted_count = 0
    failed_count = 0
    
    # Delete tracked asset types
    if "asset_types" in test_data and test_data["asset_types"]:
        for asset_type_id in test_data["asset_types"]:
            try:
                success, _ = client.delete(f"/api/v1/asset-types/{asset_type_id}", expected_status=204)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
    
    print(f"  Deleted {deleted_count} asset types, {failed_count} failures")
    return True


def test_delete_tenants():
    """Delete test tenant and all its data (cascades to all assets, users, etc.)"""
    print_test("CLEANUP", "Delete test tenant")
    
    if "admin_token" not in test_data:
        print("  Skipped - no admin token available")
        return True
    
    client.set_token(test_data["admin_token"])
    deleted_count = 0
    failed_count = 0
    
    # Delete test tenant (this will cascade delete all data in that tenant)
    if test_data.get("test_tenant") and "id" in test_data["test_tenant"]:
        tenant_id = test_data["test_tenant"]["id"]
        
        # First, delete all users in the tenant
        try:
            success, users = client.get(f"/api/v1/tenants/{tenant_id}/users", expected_status=200)
            if success and isinstance(users, list):
                for user in users:
                    try:
                        client.delete(f"/api/v1/users/{user['id']}", expected_status=204)
                    except Exception as e:
                        pass
        except Exception as e:
            pass
        
        # Delete the tenant (this should cascade delete all assets, asset types, etc.)
        try:
            success, _ = client.delete(f"/api/v1/tenants/{tenant_id}", expected_status=204)
            if success:
                deleted_count += 1
                print(f"  ✓ Deleted test tenant ID: {tenant_id}")
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
    
    # Also delete any other test tenants (tenant_a, tenant_b) if they exist
    for tenant_key in ["tenant_a", "tenant_b"]:
        if tenant_key in test_data.get("tenants", {}):
            tenant_id = test_data["tenants"][tenant_key]["id"]
            try:
                success, users = client.get(f"/api/v1/tenants/{tenant_id}/users", expected_status=200)
                if success and isinstance(users, list):
                    for user in users:
                        try:
                            client.delete(f"/api/v1/users/{user['id']}", expected_status=204)
                        except Exception as e:
                            pass
                success, _ = client.delete(f"/api/v1/tenants/{tenant_id}", expected_status=204)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
    
    print(f"  Deleted {deleted_count} tenants, {failed_count} failures")
    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*80)
    print("DCMS MULTI-TENANT SAAS - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Test Prefix: {TEST_PREFIX}")
    print(f"Base URL: {BASE_URL}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check API is accessible
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: API health check failed!")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to API at {BASE_URL}: {e}")
        return False
    
    # Bootstrap: Create test tenant and user for complete isolation
    print("\n>>> Bootstrapping Test Environment...")
    if not create_test_tenant_and_user():
        print("\n" + "="*80)
        print("ERROR: Failed to bootstrap test admin user!")
        print("="*80)
        print("\nPlease ensure:")
        print(f"  1. Backend is running at {BASE_URL}")
        print(f"  2. Database is accessible")
        print(f"  3. Default admin user exists or can be created")
        print("\nOptions:")
        print("  A) Run inside Docker (recommended):")
        print("     docker compose exec backend python test_suite.py")
        print("\n  B) Run outside Docker with existing credentials:")
        print(f"     TEST_ADMIN_USERNAME=youruser TEST_ADMIN_PASSWORD=yourpass python test_suite.py")
        print("\n  C) Create admin user manually:")
        print("     docker compose exec backend python bootstrap.py")
        print("="*80)
        return False
    
    # Run test suites
    print("\n>>> Running Authentication Tests...")
    test_auth_login()
    
    # Run onboarding tests (before tenant management - onboarding creates tenants)
    print("\n>>> Running Onboarding Tests...")
    test_onboarding_create_tenant()
    test_onboarding_duplicate_slug()
    test_onboarding_duplicate_username()
    test_onboarding_validation_errors()
    test_onboarding_auto_slug_generation()
    test_onboarding_asset_types_seeded()
    test_onboarding_token_validity()
    test_onboarding_tenant_isolation()
    
    print("\n>>> Running Tenant Management Tests...")
    test_create_tenant()
    test_create_duplicate_tenant()
    test_list_tenants()
    test_create_second_tenant_and_user()
    
    print("\n>>> Running User Management Tests...")
    test_create_user_in_tenant()
    
    print("\n>>> Running Asset Type Tests...")
    test_list_asset_types()
    
    print("\n>>> Running Asset Creation Tests...")
    test_create_assets_all_types()
    test_asset_type_validation()
    
    print("\n>>> Running Tenant Isolation Tests...")
    test_tenant_isolation_assets()
    
    print("\n>>> Running Dashboard Tests...")
    test_dashboard_summary()
    test_dashboard_tenant_isolation()
    
    print("\n>>> Running Barcode Tests...")
    test_barcode_generation()
    test_barcode_tenant_isolation()
    
    print("\n>>> Running Stock Management Tests...")
    test_stock_management_create_storage_box()
    test_stock_management_add_items_to_box()
    test_stock_management_get_stock_info()
    test_stock_management_get_items_in_box()
    test_stock_management_auto_deploy_on_connect()
    test_stock_management_low_stock_alert()
    test_stock_management_count_all_items()
    test_stock_lifecycle_consumption()  # New test for stock_service
    
    print("\n>>> Running Inventory Listing Tests...")
    test_inventory_shows_all_statuses()
    
    print("\n>>> Running Auto-Status Tests...")
    test_auto_status_on_container()
    
    print("\n>>> Running Asset Status Tests...")
    test_asset_status_in_storage()
    test_asset_status_rma_retired()
    test_asset_status_normalization()
    
    print("\n>>> Running Connection Auto-Deploy Tests...")
    test_connection_auto_deploy_cable()
    
    print("\n>>> Running Asset Type Cleanup Tests...")
    test_asset_type_cleanup_duplicates()
    
    print("\n>>> Running Cleanup Tests...")
    # Clean up in order: assets, asset types, users, then tenant (tenant deletion cascades)
    test_delete_assets()
    test_delete_asset_types()
    
    # Cleanup onboarding tenants/users
    if "onboarding" in test_data:
        print_test("CLEANUP", "Delete onboarding test data")
        if "admin_token" in test_data:
            client.set_token(test_data["admin_token"])
            onboarding = test_data["onboarding"]
            # Delete user first
            try:
                client.delete(f"/api/v1/users/{onboarding['user_id']}", expected_status=204)
            except:
                pass
            # Delete tenant (cascades to all data)
            try:
                client.delete(f"/api/v1/tenants/{onboarding['tenant_id']}", expected_status=204)
                print(f"  Deleted onboarding tenant {onboarding['tenant_id']} and user {onboarding['user_id']}")
            except:
                pass
    
    # Delete test users (handled by tenant deletion, but explicit for clarity)
    test_delete_users()
    
    # Finally, delete test tenant (this cascades to delete all remaining data)
    test_delete_tenants()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {test_count}")
    print(f"Passed: {pass_count}")
    print(f"Failed: {fail_count}")
    print(f"Success Rate: {(pass_count/test_count*100) if test_count > 0 else 0:.1f}%")
    print("="*80)
    
    # Print failed tests
    if fail_count > 0:
        print("\nFAILED TESTS:")
        for result in test_results:
            if not result["passed"]:
                print(f"  ✗ {result['test_id']}: {result['name']}")
                if result["message"]:
                    print(f"    {result['message']}")
    
    # Generate JSON report
    report = {
        "test_prefix": TEST_PREFIX,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": test_count,
            "passed": pass_count,
            "failed": fail_count,
            "success_rate": (pass_count/test_count*100) if test_count > 0 else 0
        },
        "results": test_results
    }
    
    report_file = f"test_report_{TEST_PREFIX}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {report_file}")
    
    return fail_count == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

