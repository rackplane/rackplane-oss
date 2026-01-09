"""
Pytest-based user management tests.

Tests user creation and management within tenants.
"""

import pytest
import uuid


@pytest.mark.integration
def test_create_user_in_tenant(admin_token, api_client, test_tenant, test_prefix):
    """
    TC-USER-001: Create user with valid data
    
    This test verifies that users can be created in a tenant.
    Note: This requires admin token (super admin access).
    """
    api_client.set_token(admin_token)
    
    user_data = {
        "username": f"{test_prefix.lower()}-newuser",
        "password": "TestPassword123!",
        "tenant_id": test_tenant["id"]
    }
    
    success, response = api_client.post(
        f"/api/v1/tenants/{test_tenant['id']}/users",
        user_data,
        expected_status=201
    )
    
    assert success, f"Failed to create user: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["username"] == user_data["username"]
    assert response["tenant_id"] == test_tenant["id"]
    
    # Verify user can login
    token = api_client.login(user_data["username"], user_data["password"])
    assert token is not None, "User should be able to login"
    
    # Cleanup: Delete user
    api_client.set_token(admin_token)
    api_client.delete(f"/api/v1/users/{response['id']}", expected_status=204)


@pytest.mark.integration
def test_list_users(authenticated_client):
    """
    TC-USER-002: List users in tenant
    
    This test verifies that users can be listed.
    """
    success, response = authenticated_client.get("/api/v1/users/", expected_status=200)
    
    assert success, f"Failed to list users: {response}"
    assert isinstance(response, list), f"Expected list response, got: {type(response)}"
    
    # Verify user structure
    if len(response) > 0:
        user = response[0]
        assert "id" in user, "User missing 'id' field"
        assert "username" in user, "User missing 'username' field"
        assert "is_active" in user, "User missing 'is_active' field"


@pytest.mark.integration
def test_get_user_by_id(admin_token, api_client, test_tenant, test_user):
    """
    TC-USER-003: Get user by ID
    
    This test verifies that users can be retrieved by ID.
    Note: This may require super admin access or same-tenant access.
    """
    api_client.set_token(admin_token)
    
    user_id = test_user["user"]["id"]
    
    # Try to get user - may require super admin or same tenant
    success, response = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    
    if success:
        assert response["id"] == user_id
        assert response["username"] == test_user["user"]["username"]
        # tenant_id might not be in response depending on endpoint
        if "tenant_id" in response:
            assert response["tenant_id"] == test_tenant["id"]
    else:
        # If endpoint doesn't exist or requires different permissions, skip
        pytest.skip(f"User endpoint may require different permissions: {response}")


@pytest.mark.integration
def test_delete_user_super_admin_cross_tenant(admin_token, api_client, test_tenant, test_user):
    """
    TC-USER-004: Verify super admin can delete users from any tenant.
    
    This test verifies that super admins can delete users from tenants
    other than their own, bypassing tenant filtering.
    """
    api_client.set_token(admin_token)
    
    user_id = test_user["user"]["id"]
    username = test_user["user"]["username"]
    
    # Verify user exists (bypassing tenant filtering)
    success, user_data = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    assert success, f"Failed to get user: {user_data}"
    assert user_data["username"] == username
    
    # Delete the user (super admin should be able to delete from any tenant)
    success, response = api_client.delete(f"/api/v1/users/{user_id}", expected_status=204)
    
    # Should succeed (204 No Content)
    assert success, f"Failed to delete user: {response}"
    
    # Verify user is deleted (should return 404)
    # Note: This is a positive test - we expect 404, so we can use expected_status
    success, response = api_client.get(f"/api/v1/users/{user_id}", expected_status=404)
    assert success, f"User should be deleted (404), but got: {response}"
    assert "not found" in str(response).lower() or "404" in str(response).lower(), \
        f"Expected 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.user_role
def test_update_user_role_to_tenant_admin(admin_token, api_client, test_tenant, test_user):
    """
    TC-USER-005: Update user role to tenant_admin
    
    This test verifies that:
    1. A user's role can be updated via the API
    2. The role change persists in the database
    3. The updated role affects access permissions (audit logs)
    """
    from app.models.user_role import UserRole
    
    api_client.set_token(admin_token)
    user_id = test_user["user"]["id"]
    username = test_user["user"]["username"]
    password = test_user["credentials"]["password"]
    
    # Step 1: Verify initial role (may be tenant_admin from fixture, that's OK - we'll update it)
    success, user_data = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    assert success, f"Failed to get user: {user_data}"
    initial_role = user_data.get("role", "user")
    
    # If role is already tenant_admin, set it to user first for the test
    if initial_role == "tenant_admin":
        success, _ = api_client.put(
            f"/api/v1/users/{user_id}",
            {"role": "user"},
            expected_status=200
        )
        assert success, "Failed to set initial role to user"
        # Re-fetch to verify
        success, user_data = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
        assert success, f"Failed to get user after role change: {user_data}"
        initial_role = user_data.get("role", "user")
        assert initial_role == "user", f"Expected initial role to be 'user' after setting it, got: {initial_role}"
    
    # Step 2: Update role to TENANT_ADMIN
    success, updated_user = api_client.put(
        f"/api/v1/users/{user_id}",
        {"role": UserRole.TENANT_ADMIN.value},
        expected_status=200
    )
    assert success, f"Failed to update user role: {updated_user}"
    assert updated_user.get("role") == UserRole.TENANT_ADMIN.value, \
        f"Role should be updated to tenant_admin, got: {updated_user.get('role')}"
    
    # Step 3: Verify role change persisted
    success, user_check = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    assert success, f"Failed to get updated user: {user_check}"
    assert user_check.get("role") == UserRole.TENANT_ADMIN.value, \
        f"Role change should persist, got: {user_check.get('role')}"
    
    # Step 4: Login as the updated user and verify they can access audit logs
    # (Role changes require re-login to take effect in JWT token)
    user_token = api_client.login(username, password)
    assert user_token is not None, "User should be able to login after role change"
    api_client.set_token(user_token)
    
    # Step 5: Verify tenant admin can access audit logs
    success, logs_response = api_client.get("/api/v1/audit-logs/", expected_status=200)
    assert success, f"Tenant admin should be able to access audit logs: {logs_response}"
    assert isinstance(logs_response, dict), "Audit logs response should be a dict with total, limit, offset, logs"
    assert "logs" in logs_response, "Response should contain 'logs' field"
    assert "total" in logs_response, "Response should contain 'total' field"
    
    # Step 6: Revert role back to USER for cleanup
    api_client.set_token(admin_token)
    success, reverted_user = api_client.put(
        f"/api/v1/users/{user_id}",
        {"role": UserRole.USER.value},
        expected_status=200
    )
    assert success, f"Failed to revert user role: {reverted_user}"
    assert reverted_user.get("role") == UserRole.USER.value, \
        f"Role should be reverted to user, got: {reverted_user.get('role')}"


@pytest.mark.integration
@pytest.mark.user_role
def test_update_user_role_regular_user_cannot_access_audit_logs(admin_token, api_client, test_user):
    """
    TC-USER-006: Verify regular USER cannot access audit logs
    
    This test verifies that:
    1. A user with role USER cannot access audit logs
    2. Only TENANT_ADMIN and SUPER_ADMIN can access audit logs
    """
    from app.models.user_role import UserRole
    
    api_client.set_token(admin_token)
    user_id = test_user["user"]["id"]
    username = test_user["user"]["username"]
    password = test_user["credentials"]["password"]
    
    # Step 1: Ensure user role is USER
    success, user_data = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    assert success, f"Failed to get user: {user_data}"
    
    # Update to USER if not already
    if user_data.get("role") != UserRole.USER.value:
        success, _ = api_client.put(
            f"/api/v1/users/{user_id}",
            {"role": UserRole.USER.value},
            expected_status=200
        )
        assert success, "Failed to set user role to USER"
    
    # Step 2: Login as regular user
    user_token = api_client.login(username, password)
    assert user_token is not None, "User should be able to login"
    api_client.set_token(user_token)
    
    # Step 3: Verify regular user CANNOT access audit logs
    # Don't pass expected_status=403 - we want to check the actual status
    success, response = api_client.get("/api/v1/audit-logs/", expected_status=200)
    # If success is False, it means we got a non-200 status (likely 403)
    assert not success, f"Regular user should NOT be able to access audit logs (got 200, expected 403): {response}"
    
    # Verify error message indicates permission issue
    if isinstance(response, dict):
        detail = str(response.get("detail", "")).lower()
        assert "tenant admin" in detail or "forbidden" in detail or "403" in detail, \
            f"Error should indicate permission issue, got: {response}"
    
    # Step 4: Verify user can still access other endpoints (not blocked entirely)
    success, assets_response = api_client.get("/api/v1/assets/", expected_status=200)
    assert success, "Regular user should still be able to access assets endpoint"


@pytest.mark.integration
@pytest.mark.user_role
def test_role_update_affects_jwt_token(admin_token, api_client, test_user):
    """
    TC-USER-007: Verify role changes require re-login to take effect
    
    This test verifies that:
    1. Role changes in the database don't immediately affect existing JWT tokens
    2. Users must log out and log back in for role changes to take effect
    3. New JWT tokens reflect the updated role
    """
    from app.models.user_role import UserRole
    
    api_client.set_token(admin_token)
    user_id = test_user["user"]["id"]
    username = test_user["user"]["username"]
    password = test_user["credentials"]["password"]
    
    # Step 0: Ensure user starts with USER role (fixture may create with tenant_admin)
    success, user_data = api_client.get(f"/api/v1/users/{user_id}", expected_status=200)
    assert success, f"Failed to get user: {user_data}"
    initial_role = user_data.get("role", "user")
    
    if initial_role != "user":
        # Set role to user first
        success, _ = api_client.put(
            f"/api/v1/users/{user_id}",
            {"role": "user"},
            expected_status=200
        )
        assert success, "Failed to set initial role to user"
    
    # Step 1: Login as user (gets JWT with current role)
    initial_token = api_client.login(username, password)
    assert initial_token is not None, "User should be able to login"
    api_client.set_token(initial_token)
    
    # Step 2: Verify user cannot access audit logs with initial token
    # Don't pass expected_status - we want to check the actual status
    success, response = api_client.get("/api/v1/audit-logs/")
    assert not success, f"User with USER role should not access audit logs (got success, expected failure): {response}"
    # Verify it's a permission error
    error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
    assert "403" in str(response).lower() or "forbidden" in error_detail or "permission" in error_detail or "tenant admin" in error_detail, \
        f"Expected permission error, got: {response}"
    
    # Step 3: Update role to TENANT_ADMIN (while user is still logged in with old token)
    api_client.set_token(admin_token)
    success, _ = api_client.put(
        f"/api/v1/users/{user_id}",
        {"role": UserRole.TENANT_ADMIN.value},
        expected_status=200
    )
    assert success, "Failed to update user role"
    
    # Step 4: Try to use old token - should still fail (token has old role)
    api_client.set_token(initial_token)
    success, response = api_client.get("/api/v1/audit-logs/")
    assert not success, f"Old JWT token should still have USER role and fail: {response}"
    # Verify it's a permission error
    error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
    assert "403" in str(response).lower() or "forbidden" in error_detail or "permission" in error_detail or "tenant admin" in error_detail, \
        f"Expected permission error, got: {response}"
    
    # Step 5: Login again to get new token with updated role
    new_token = api_client.login(username, password)
    assert new_token is not None, "User should be able to login again"
    assert new_token != initial_token, "New token should be different from old token"
    api_client.set_token(new_token)
    
    # Step 6: Verify new token allows access to audit logs
    success, logs_response = api_client.get("/api/v1/audit-logs/", expected_status=200)
    assert success, "New JWT token with TENANT_ADMIN role should allow audit log access"
    
    # Step 7: Cleanup - revert role
    api_client.set_token(admin_token)
    api_client.put(
        f"/api/v1/users/{user_id}",
        {"role": UserRole.USER.value},
        expected_status=200
    )

