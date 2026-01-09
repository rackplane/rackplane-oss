# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Environmental Monitoring API Test Suite
Tests for environmental sensors and readings.
"""

import pytest


@pytest.mark.integration
@pytest.mark.environmental
def test_list_sensors(authenticated_client):
    """
    TC-ENV-001: List environmental sensors
    """
    success, response = authenticated_client.get("/api/v1/environmental/sensors", expected_status=200)
    
    assert success, f"Failed to list sensors: {response}"
    assert isinstance(response, list), "Response should be a list"


@pytest.mark.integration
@pytest.mark.environmental
def test_get_readings(authenticated_client):
    """
    TC-ENV-002: Get sensor readings
    """
    success, response = authenticated_client.get("/api/v1/environmental/readings", expected_status=200)
    
    assert success, f"Failed to get readings: {response}"
    assert isinstance(response, list), "Response should be a list"


@pytest.mark.integration
@pytest.mark.environmental
def test_get_latest_readings(authenticated_client):
    """
    TC-ENV-003: Get latest sensor readings
    """
    success, response = authenticated_client.get("/api/v1/environmental/readings/latest", expected_status=200)
    
    assert success, f"Failed to get latest readings: {response}"
    # Response structure may vary, but should not error


@pytest.mark.integration
@pytest.mark.environmental
def test_get_anomalies(authenticated_client):
    """
    TC-ENV-004: Get anomalous readings
    """
    success, response = authenticated_client.get("/api/v1/environmental/readings/anomalies", expected_status=200)
    
    assert success, f"Failed to get anomalies: {response}"
    assert isinstance(response, list), "Response should be a list"


@pytest.mark.integration
@pytest.mark.environmental
def test_get_threshold_breaches(authenticated_client):
    """
    TC-ENV-005: Get threshold breaches
    """
    success, response = authenticated_client.get("/api/v1/environmental/readings/threshold-breaches", expected_status=200)
    
    assert success, f"Failed to get threshold breaches: {response}"
    assert isinstance(response, list), "Response should be a list"


@pytest.mark.integration
@pytest.mark.environmental
def test_get_active_alerts(authenticated_client):
    """
    TC-ENV-006: Get active environmental alerts
    """
    success, response = authenticated_client.get("/api/v1/environmental/alerts/active", expected_status=200)
    
    assert success, f"Failed to get active alerts: {response}"
    # Response structure may vary, but should not error


@pytest.mark.integration
@pytest.mark.environmental
def test_environmental_get_nonexistent_sensor(authenticated_client):
    """
    TC-ENV-007: Get non-existent sensor should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.get(f"/api/v1/environmental/sensors/{nonexistent_id}", expected_status=404)
    assert success, "Should return 404 for non-existent sensor"

