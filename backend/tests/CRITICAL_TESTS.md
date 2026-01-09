# Critical Test Suite

## Overview

The critical test suite contains tests that **MUST PASS** after any system change. These tests verify core functionality that, if broken, would cause serious issues in production.

## When to Run Critical Tests

Run these tests after:
- ✅ **Database migrations** - Verify constraints and data integrity
- ✅ **Authentication/authorization changes** - Verify security
- ✅ **Multi-tenancy changes** - Verify tenant isolation
- ✅ **Backup/restore changes** - Verify data preservation
- ✅ **Data model changes** - Verify CRUD operations
- ✅ **Any deployment** - Final verification before going live

## Running Critical Tests

### Quick Run
```bash
# Run critical tests only
docker compose exec backend python3 -m pytest tests/ -m critical -v

# Or use the convenience script
docker compose exec backend python3 scripts/run_critical_tests.py
```

### With Coverage
```bash
docker compose exec backend python3 scripts/run_critical_tests.py --coverage
```

### Exit on First Failure
```bash
docker compose exec backend python3 scripts/run_critical_tests.py -x
```

## Test Categories

### 1. Authentication & Authorization (3 tests)
- `test_auth_login` - Valid credentials must work
- `test_auth_invalid_token` - Invalid tokens must be rejected
- `test_super_admin_can_manage_tenants` - Super admin permissions

**Why Critical**: Security is fundamental. Broken auth = broken system.

### 2. Data Integrity - Duplicate Prevention (3 tests)
- `test_user_duplicate_username` - Username uniqueness per tenant
- `test_rack_duplicate_code` - Rack code uniqueness per tenant
- `test_storage_container_duplicate_name` - Container name uniqueness per tenant

**Why Critical**: Prevents data corruption. We've had 77,820 duplicate users before.

### 3. Multi-Tenancy Isolation (1 test)
- `test_tenant_isolation` - Tenants cannot see each other's data

**Why Critical**: Data leakage between tenants is a security issue.

### 4. Migration Idempotency (3 tests)
- `test_print_jobs_migration_is_fully_idempotent` - Migrations can be run multiple times
- `test_all_migrations_can_be_applied_twice` - All migrations are idempotent
- `test_migration_file_syntax_is_valid` - All migration files are valid Python

**Why Critical**: Migration failures cause deployment failures. We've had multiple instances where migrations failed because enum types already existed. These tests prevent that.

### 5. Basic CRUD Operations (1 test)
- `test_basic_asset_crud` - Create, Read, Update, Delete must work

**Why Critical**: If CRUD is broken, the system is unusable.

### 5. Backup/Restore (1 test)
- `test_backup_restore_basic` - Backup creation must work

**Why Critical**: Data loss prevention. Backups must work.

## Test Details

### Authentication Tests
```python
@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.auth
def test_auth_login(authenticated_client):
    """CRITICAL: Authentication must work for system to function."""
```

### Duplicate Prevention Tests
```python
@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_user_duplicate_username(admin_token, api_client, test_tenant):
    """CRITICAL: Username uniqueness per tenant must be enforced."""
```

### Tenant Isolation Tests
```python
@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.tenant
def test_tenant_isolation(test_tenant, authenticated_client):
    """CRITICAL: Tenant isolation must work to prevent data leakage."""
```

## Adding New Critical Tests

When adding a new critical test:

1. **Mark it with `@pytest.mark.critical`**
2. **Add it to `test_critical_smoke_pytest.py`** or mark existing test
3. **Document why it's critical** in the docstring
4. **Keep it fast** - Critical tests should complete in < 30 seconds total
5. **Make it independent** - Should not depend on other tests

Example:
```python
@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.your_category
def test_something_critical(authenticated_client):
    """
    CRITICAL: Brief explanation of why this must pass.
    """
    # Test implementation
    pass
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Critical Tests
  run: |
    docker compose exec backend python3 scripts/run_critical_tests.py -x
```

### Pre-Deployment Checklist
- [ ] All critical tests pass locally
- [ ] All critical tests pass in CI
- [ ] No new critical test failures
- [ ] Migration safety check passes (if migration changed)

## Test Execution Time

**Target**: < 30 seconds total
**Current**: ~15-20 seconds

If critical tests exceed 30 seconds, consider:
- Optimizing slow tests
- Splitting into parallel execution
- Removing non-essential checks

## Troubleshooting

### Tests Fail After Migration
1. Check migration safety: `python3 scripts/check_migration_safety.py`
2. Verify database constraints exist
3. Check for duplicate data
4. Review migration downgrade() function

### Tests Fail After Code Change
1. Review the change for side effects
2. Check if change affects authentication/authorization
3. Verify tenant isolation still works
4. Check if duplicate prevention logic changed

### Tests Timeout
1. Check database connection
2. Verify test fixtures are working
3. Check for deadlocks or long-running queries
4. Review test isolation

## Related Documentation

- `MIGRATION_SAFETY_GUIDE.md` - Database migration safety
- `README.md` - Full test suite documentation
- `pytest.ini` - Pytest configuration

