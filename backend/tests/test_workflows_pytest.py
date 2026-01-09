# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Workflows API Test Suite
Tests for workflow templates, executions, and steps.
"""

import pytest
from app.models.workflow import WorkflowType, WorkflowStatus


@pytest.mark.integration
@pytest.mark.workflow
def test_list_workflow_templates(authenticated_client):
    """
    TC-WORKFLOW-001: List workflow templates
    """
    success, response = authenticated_client.get("/api/v1/workflows/templates", expected_status=200)
    
    assert success, f"Failed to list workflow templates: {response}"
    assert isinstance(response, list), "Response should be a list"


@pytest.mark.integration
@pytest.mark.workflow
def test_list_workflow_executions(authenticated_client):
    """
    TC-WORKFLOW-002: List workflow executions
    """
    success, response = authenticated_client.get("/api/v1/workflows/executions", expected_status=200)
    
    assert success, f"Failed to list workflow executions: {response}"
    assert "total" in response, "Response should include total count"
    assert "executions" in response, "Response should include executions list"
    assert isinstance(response["executions"], list)


@pytest.mark.integration
@pytest.mark.workflow
def test_workflow_get_nonexistent_template(authenticated_client):
    """
    TC-WORKFLOW-003: Get non-existent workflow template should return 404
    """
    nonexistent_id = 999999
    
    # Don't pass expected_status - we want to check the actual status
    success, response = authenticated_client.get(f"/api/v1/workflows/templates/{nonexistent_id}")
    assert not success, f"Should return 404 for non-existent template, got success: {response}"
    # Verify it's a 404 error
    error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
    assert "404" in str(response).lower() or "not found" in error_detail, \
        f"Expected 404 not found error, got: {response}"


@pytest.mark.integration
@pytest.mark.workflow
def test_workflow_get_nonexistent_execution(authenticated_client):
    """
    TC-WORKFLOW-004: Get non-existent workflow execution should return 404
    """
    nonexistent_id = 999999
    
    # Don't pass expected_status - we want to check the actual status
    success, response = authenticated_client.get(f"/api/v1/workflows/executions/{nonexistent_id}")
    assert not success, f"Should return 404 for non-existent execution, got success: {response}"
    # Verify it's a 404 error
    error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
    assert "404" in str(response).lower() or "not found" in error_detail, \
        f"Expected 404 not found error, got: {response}"

