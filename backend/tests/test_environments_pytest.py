# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Environments API Test Suite
Tests for DEV troubleshooting environment management.
"""

import pytest


@pytest.mark.integration
@pytest.mark.environment
def test_create_environment(authenticated_client, test_prefix):
    """
    TC-ENV-001: Create environment
    """
    env_data = {
        "name": f"{test_prefix}-ENV-001",
        "ssh_link": "test-ssh.example.com",
        "ipmi_link": "https://ipmi.test.example.com",
        "ssh_username": "testuser",
        "ssh_password": "testpass",
        "ipmi_username": "admin",
        "ipmi_password": "admin"
    }
    
    success, response = authenticated_client.post("/api/v1/environments/", env_data, expected_status=201)
    
    assert success, f"Failed to create environment: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["name"] == env_data["name"]
    assert response["ssh_link"] == env_data["ssh_link"]
    assert response["ipmi_link"] == env_data["ipmi_link"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/environments/{response['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.environment
def test_list_environments(authenticated_client, test_prefix):
    """
    TC-ENV-002: List environments
    """
    # Create a test environment
    env_data = {
        "name": f"{test_prefix}-ENV-LIST-001",
        "ssh_link": "test-ssh.example.com",
        "ipmi_link": "https://ipmi.test.example.com"
    }
    
    success, created = authenticated_client.post("/api/v1/environments/", env_data, expected_status=201)
    assert success, f"Failed to create environment: {created}"
    env_id = created["id"]
    
    # List environments
    success, response = authenticated_client.get("/api/v1/environments/", expected_status=200)
    
    assert success, f"Failed to list environments: {response}"
    assert isinstance(response, list), f"Expected list response, got: {type(response)}"
    assert len(response) > 0, "Should have at least one environment"
    
    # Find our test environment
    test_env = next((e for e in response if e["id"] == env_id), None)
    assert test_env is not None, "Test environment should be in the list"
    assert test_env["name"] == env_data["name"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/environments/{env_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.environment
def test_get_environment_by_id(authenticated_client, test_prefix):
    """
    TC-ENV-003: Get environment by ID
    """
    # Create environment
    env_data = {
        "name": f"{test_prefix}-ENV-GET-001",
        "ssh_link": "test-ssh.example.com",
        "ipmi_link": "https://ipmi.test.example.com"
    }
    
    success, created = authenticated_client.post("/api/v1/environments/", env_data, expected_status=201)
    assert success, f"Failed to create environment: {created}"
    env_id = created["id"]
    
    # Get by ID
    success, fetched = authenticated_client.get(f"/api/v1/environments/{env_id}", expected_status=200)
    
    assert success, f"Failed to fetch environment: {fetched}"
    assert fetched["id"] == env_id
    assert fetched["name"] == env_data["name"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/environments/{env_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.environment
def test_update_environment(authenticated_client, test_prefix):
    """
    TC-ENV-004: Update environment
    """
    # Create environment
    env_data = {
        "name": f"{test_prefix}-ENV-UPDATE-001",
        "ssh_link": "test-ssh.example.com",
        "ipmi_link": "https://ipmi.test.example.com"
    }
    
    success, created = authenticated_client.post("/api/v1/environments/", env_data, expected_status=201)
    assert success, f"Failed to create environment: {created}"
    env_id = created["id"]
    
    # Update environment
    update_data = {
        "ssh_link": "updated-ssh.example.com",
        "ipmi_link": "https://updated-ipmi.example.com",
        "ssh_username": "updateduser"
    }
    
    success, updated = authenticated_client.put(f"/api/v1/environments/{env_id}", update_data, expected_status=200)
    
    assert success, f"Failed to update environment: {updated}"
    assert updated["ssh_link"] == update_data["ssh_link"]
    assert updated["ipmi_link"] == update_data["ipmi_link"]
    assert updated["ssh_username"] == update_data["ssh_username"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/environments/{env_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.environment
def test_delete_environment(authenticated_client, test_prefix):
    """
    TC-ENV-005: Delete environment
    """
    # Create environment
    env_data = {
        "name": f"{test_prefix}-ENV-DELETE-001",
        "ssh_link": "test-ssh.example.com",
        "ipmi_link": "https://ipmi.test.example.com"
    }
    
    success, created = authenticated_client.post("/api/v1/environments/", env_data, expected_status=201)
    assert success, f"Failed to create environment: {created}"
    env_id = created["id"]
    
    # Delete environment (may return 200 or 204)
    success, response = authenticated_client.delete(f"/api/v1/environments/{env_id}", expected_status=[200, 204])
    
    assert success, f"Failed to delete environment: {response}"
    
    # Verify it's deleted (may return 404 or 200 with error)
    success, fetched = authenticated_client.get(f"/api/v1/environments/{env_id}", expected_status=[200, 404])
    if success:
        error_detail = str(fetched.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {fetched}"
    else:
        assert "not found" in str(fetched).lower() or fetched.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {fetched}"


@pytest.mark.integration
@pytest.mark.environment
def test_environment_get_nonexistent(authenticated_client):
    """
    TC-ENV-006: Get non-existent environment should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.get(f"/api/v1/environments/{nonexistent_id}", expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"

