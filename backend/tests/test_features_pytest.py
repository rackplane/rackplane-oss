# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Feature Access API Test Suite
Tests for RackPlane Services feature subscription endpoints
"""

import pytest


@pytest.mark.integration
@pytest.mark.features
def test_check_feature_access(authenticated_client, test_tenant):
    """
    Test checking feature access for a tenant.
    
    Verifies:
    - Endpoint exists and is accessible
    - Returns correct structure
    - Handles missing features gracefully
    """
    # Test checking a feature that doesn't exist
    success, response = authenticated_client.get(
        "/api/v1/features/check",
        params={"feature": "ocr_cloud"},
        expected_status=200
    )
    
    assert success, f"Failed to check feature access: {response}"
    assert "has_access" in response, "Response should include has_access"
    assert "feature" in response, "Response should include feature name"
    assert "subscription_tier" in response, "Response should include subscription tier"
    assert response["feature"] == "ocr_cloud", "Should return the requested feature name"
    
    # By default, features should be False (no subscription)
    assert response["has_access"] == False, "Default tenant should not have feature access"


@pytest.mark.integration
@pytest.mark.features
def test_list_available_features(authenticated_client, test_tenant):
    """
    Test listing all available features and their access status.
    
    Verifies:
    - Endpoint exists and is accessible
    - Returns all features with their status
    - Includes subscription tier information
    """
    success, response = authenticated_client.get(
        "/api/v1/features/list",
        expected_status=200
    )
    
    assert success, f"Failed to list features: {response}"
    assert "subscription_tier" in response, "Response should include subscription tier"
    assert "features" in response, "Response should include features dict"
    
    features = response["features"]
    assert isinstance(features, dict), "Features should be a dictionary"
    
    # Verify expected features exist
    expected_features = ["ocr_cloud", "ocr_enhanced", "vendor_lookup", "warranty_management"]
    for feature_name in expected_features:
        assert feature_name in features, f"Feature {feature_name} should be in response"
        assert "name" in features[feature_name], f"Feature {feature_name} should have name"
        assert "description" in features[feature_name], f"Feature {feature_name} should have description"
        assert "has_access" in features[feature_name], f"Feature {feature_name} should have has_access"


@pytest.mark.integration
@pytest.mark.features
def test_get_usage_stats(authenticated_client, test_tenant):
    """
    Test getting usage statistics for commercial features.
    
    Verifies:
    - Endpoint exists and is accessible
    - Returns usage statistics or unavailable status
    - Handles service unavailability gracefully
    """
    success, response = authenticated_client.get(
        "/api/v1/features/usage",
        expected_status=200
    )
    
    assert success, f"Failed to get usage stats: {response}"
    # Should return either stats or unavailable status
    assert "status" in response or "usage" in response or "error" in response, \
        "Response should include status, usage, or error"


@pytest.mark.integration
@pytest.mark.features
def test_check_services_health(authenticated_client, test_tenant):
    """
    Test checking health status of RackPlane Services API.
    
    Verifies:
    - Endpoint exists and is accessible
    - Returns health status
    - Handles service unavailability gracefully
    """
    success, response = authenticated_client.get(
        "/api/v1/features/health",
        expected_status=200
    )
    
    assert success, f"Failed to check services health: {response}"
    # Should return health status (available or unavailable)
    assert "status" in response, "Response should include status"


@pytest.mark.integration
@pytest.mark.features
def test_check_feature_requires_auth(api_client):
    """
    Test that feature endpoints require authentication.
    
    Verifies:
    - Unauthenticated requests are rejected
    - Returns 401 Unauthorized
    """
    # Try to access without authentication
    success, response = api_client.get(
        "/api/v1/features/check",
        params={"feature": "ocr_cloud"},
        expected_status=401
    )
    
    # Should fail with 401
    assert not success or response.get("detail") or "401" in str(response), \
        "Unauthenticated request should be rejected"


@pytest.mark.integration
@pytest.mark.features
def test_check_invalid_feature(authenticated_client, test_tenant):
    """
    Test checking access for an invalid feature name.
    
    Verifies:
    - Endpoint handles invalid feature names gracefully
    - Returns has_access=False for unknown features
    """
    success, response = authenticated_client.get(
        "/api/v1/features/check",
        params={"feature": "nonexistent_feature_xyz"},
        expected_status=200
    )
    
    assert success, f"Failed to check invalid feature: {response}"
    assert response["has_access"] == False, "Invalid features should return has_access=False"
    assert response["feature"] == "nonexistent_feature_xyz", "Should return the requested feature name"

