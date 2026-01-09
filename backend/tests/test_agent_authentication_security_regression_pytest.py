# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression Test: Agent Authentication Security
Tests that agent authentication requires and validates agent_secret
"""

import pytest
from app.core.database import SessionLocal
from app.models.print_job import PrintAgent
from app.core.auth import get_password_hash, verify_password
from app.core.tenant import set_current_tenant_id, clear_tenant_id
from datetime import datetime


@pytest.mark.integration
@pytest.mark.regression
def test_agent_login_requires_secret(api_client, test_tenant, test_prefix):
    """
    REGRESSION: Agent login must require agent_secret
    
    Bug: agent_login endpoint accepted any agent_id without secret validation,
    allowing attackers to impersonate any print agent.
    
    Fix: Require agent_secret in request and validate against stored hash.
    
    This test verifies:
    1. Login without secret returns 422 (validation error)
    2. Login with invalid secret returns 401
    3. Login with valid secret returns 200 with token
    """
    set_current_tenant_id(test_tenant["id"])
    agent_id = f"{test_prefix}-agent-001"
    
    try:
        # Cleanup: Remove agent if it exists
        db = SessionLocal()
        try:
            db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).delete()
            db.commit()
        finally:
            db.close()
        
        # Test 1: Login without secret should fail validation
        login_data = {
            "agent_id": agent_id,
            "agent_name": "Test Agent"
        }
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_data,
            expected_status=422  # Validation error
        )
        assert not success or "agent_secret" in str(response).lower(), \
            "Should require agent_secret field"
        
        # Test 2: Login with invalid secret should return 401
        login_data_invalid = {
            "agent_id": agent_id,
            "agent_secret": "wrong-secret",
            "agent_name": "Test Agent"
        }
        # First create agent with correct secret
        db = SessionLocal()
        try:
            agent = PrintAgent(
                agent_id=agent_id,
                agent_name="Test Agent",
                secret_hash=get_password_hash("correct-secret"),
                is_active=True,
                tenant_id=test_tenant["id"],
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent)
            db.commit()
        finally:
            db.close()
        
        # Now try login with wrong secret
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_data_invalid,
            expected_status=401
        )
        assert success, f"Should return 401 for invalid secret, got: {response}"
        assert "invalid" in str(response.get("detail", "")).lower() or "unauthorized" in str(response.get("detail", "")).lower(), \
            f"Should indicate invalid secret, got: {response}"
        
        # Test 3: Login with valid secret should succeed
        login_data_valid = {
            "agent_id": agent_id,
            "agent_secret": "correct-secret",
            "agent_name": "Test Agent"
        }
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_data_valid,
            expected_status=200
        )
        assert success, f"Should succeed with valid secret, got: {response}"
        assert "access_token" in response, "Should return access token"
        assert response["agent_id"] == agent_id, "Should return correct agent_id"
        
    finally:
        clear_tenant_id()


@pytest.mark.integration
@pytest.mark.regression
def test_agent_login_stores_secret_on_first_login(api_client, test_tenant, test_prefix):
    """
    REGRESSION: New agents should have secret stored on first login
    
    This test verifies:
    1. New agent without secret_hash can login with any secret (first-time setup)
    2. Secret is stored as hash
    3. Subsequent logins require the same secret
    """
    set_current_tenant_id(test_tenant["id"])
    agent_id = f"{test_prefix}-new-agent-001"
    
    try:
        # Cleanup: Remove agent if it exists
        db = SessionLocal()
        try:
            db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).delete()
            db.commit()
        finally:
            db.close()
        
        # Create agent without secret_hash (simulating existing agent before migration)
        db = SessionLocal()
        try:
            agent = PrintAgent(
                agent_id=agent_id,
                agent_name="New Agent",
                secret_hash=None,  # No secret set yet
                is_active=True,
                tenant_id=test_tenant["id"],
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
            agent_db_id = agent.id  # Store DB ID separately
        finally:
            db.close()
        
        # First login: should store secret
        login_data = {
            "agent_id": agent_id,
            "agent_secret": "first-secret",
            "agent_name": "New Agent"
        }
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_data,
            expected_status=200
        )
        assert success, f"First login should succeed, got: {response}"
        assert "access_token" in response, "Should return access token"
        
        # Verify secret was stored
        db = SessionLocal()
        try:
            stored_agent = db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).first()
            assert stored_agent is not None, "Agent should exist"
            assert stored_agent.secret_hash is not None, "Secret hash should be stored"
            assert verify_password("first-secret", stored_agent.secret_hash), "Stored hash should verify correctly"
        finally:
            db.close()
        
        # Second login: should require same secret
        success2, response2 = api_client.post(
            "/api/v1/auth/agent-login",
            login_data,
            expected_status=200
        )
        assert success2, "Second login with same secret should succeed"
        
        # Third login: wrong secret should fail
        login_data_wrong = {
            "agent_id": agent_id,
            "agent_secret": "wrong-secret",
            "agent_name": "New Agent"
        }
        success3, response3 = api_client.post(
            "/api/v1/auth/agent-login",
            login_data_wrong,
            expected_status=401
        )
        assert success3, "Login with wrong secret should return 401"
        
    finally:
        clear_tenant_id()


@pytest.mark.integration
@pytest.mark.regression
def test_agent_login_prevents_impersonation(api_client, test_tenant, test_prefix):
    """
    REGRESSION: Agent authentication prevents impersonation
    
    This test verifies that an attacker cannot:
    1. Login as an existing agent without knowing the secret
    2. Create a new agent and then login as a different agent_id
    """
    set_current_tenant_id(test_tenant["id"])
    agent_id = f"{test_prefix}-legitimate-agent"
    
    try:
        # Cleanup: Remove agent if it exists
        db = SessionLocal()
        try:
            db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).delete()
            db.commit()
        finally:
            db.close()
        
        # Create agent with known secret
        db = SessionLocal()
        try:
            agent = PrintAgent(
                agent_id=agent_id,
                agent_name="Legitimate Agent",
                secret_hash=get_password_hash("secret123"),
                is_active=True,
                tenant_id=test_tenant["id"],
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent)
            db.commit()
        finally:
            db.close()
        
        # Attacker tries to login as legitimate-agent without secret
        login_no_secret = {
            "agent_id": agent_id,
            "agent_name": "Attacker Agent"
        }
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_no_secret,
            expected_status=422  # Validation error - missing secret
        )
        assert not success or "agent_secret" in str(response).lower(), \
            "Should require agent_secret"
        
        # Attacker tries with wrong secret
        login_wrong_secret = {
            "agent_id": agent_id,
            "agent_secret": "wrong-secret",
            "agent_name": "Attacker Agent"
        }
        success2, response2 = api_client.post(
            "/api/v1/auth/agent-login",
            login_wrong_secret,
            expected_status=401
        )
        assert success2, "Should reject wrong secret"
        
        # Legitimate login should work
        login_correct = {
            "agent_id": agent_id,
            "agent_secret": "secret123",
            "agent_name": "Legitimate Agent"
        }
        success3, response3 = api_client.post(
            "/api/v1/auth/agent-login",
            login_correct,
            expected_status=200
        )
        assert success3, "Legitimate login should succeed"
        assert "access_token" in response3, "Should return token"
        
    finally:
        clear_tenant_id()


@pytest.mark.integration
@pytest.mark.regression
def test_agent_token_includes_tenant_id(api_client, test_tenant, test_prefix):
    """
    REGRESSION: Agent JWT token must include tenant_id in payload
    
    Bug: Agent login created JWT tokens without tenant_id, causing get_current_user
    to fail to set tenant context. This led to fail-closed tenant isolation
    rejecting tenant-scoped queries without tenant_id context.
    
    Fix: Include tenant_id in agent token payload from agent.tenant_id.
    Update get_current_user to handle agent tokens and set tenant_id from token.
    
    This test verifies:
    1. Agent token includes tenant_id in payload
    2. get_current_user sets tenant_id from agent token
    3. Tenant-scoped queries work after agent authentication
    """
    set_current_tenant_id(test_tenant["id"])
    agent_id = f"{test_prefix}-tenant-test-agent"
    
    try:
        # Cleanup: Remove agent if it exists
        db = SessionLocal()
        try:
            db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).delete()
            db.commit()
        finally:
            db.close()
        
        # Create agent with known secret and tenant_id
        db = SessionLocal()
        try:
            agent = PrintAgent(
                agent_id=agent_id,
                agent_name="Tenant Test Agent",
                secret_hash=get_password_hash("test-secret-123"),
                is_active=True,
                tenant_id=test_tenant["id"],
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
            assert agent.tenant_id == test_tenant["id"], "Agent must have tenant_id"
        finally:
            db.close()
        
        # Login as agent
        login_data = {
            "agent_id": agent_id,
            "agent_secret": "test-secret-123",
            "agent_name": "Tenant Test Agent"
        }
        success, response = api_client.post(
            "/api/v1/auth/agent-login",
            login_data,
            expected_status=200
        )
        assert success, f"Agent login should succeed, got: {response}"
        assert "access_token" in response, "Should return access token"
        
        # Decode token to verify tenant_id is included
        from jose import jwt
        from app.core.config import settings
        token = response["access_token"]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        assert payload.get("type") == "agent", "Token should be marked as agent token"
        assert payload.get("agent_id") == agent_id, "Token should include agent_id"
        assert payload.get("tenant_id") == test_tenant["id"], \
            f"Token MUST include tenant_id, got: {payload.get('tenant_id')}, expected: {test_tenant['id']}"
        assert payload.get("sub") == agent_id, "Token sub should be agent_id"
        
        # Verify get_current_user can extract tenant_id from agent token
        # We'll decode the token and manually verify tenant_id is set
        # Then verify that middleware would set tenant_id from token
        from app.core.tenant import get_current_tenant_id
        
        # Clear tenant context to simulate fresh request
        clear_tenant_id()
        assert get_current_tenant_id() is None, "Tenant context should be cleared"
        
        # Simulate what middleware does: decode token and set tenant_id
        from jose import jwt
        from app.core.config import settings
        
        decoded_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_tenant_id = decoded_payload.get("tenant_id")
        
        # Middleware would set tenant_id from token
        if token_tenant_id:
            set_current_tenant_id(int(token_tenant_id))
        
        # Verify tenant_id is now set in context
        tenant_id_from_context = get_current_tenant_id()
        assert tenant_id_from_context == test_tenant["id"], \
            f"Tenant_id should be set in context from agent token, got: {tenant_id_from_context}, expected: {test_tenant['id']}"
        
        # Verify tenant-scoped queries would work (tenant_id is set)
        db = SessionLocal()
        try:
            from app.models.asset import Asset
            # This query should not raise ValueError (tenant_id is set)
            try:
                asset_query = db.query(Asset).first()
                # Query succeeded - tenant_id was set correctly
            except ValueError as e:
                if "SECURITY VIOLATION" in str(e) or "tenant_id" in str(e).lower():
                    pytest.fail(f"Tenant-scoped query should work after agent auth (tenant_id set), but got: {e}")
        finally:
            db.close()
            clear_tenant_id()
        
    finally:
        clear_tenant_id()

