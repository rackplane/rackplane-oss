# RackPlane Troubleshooting Guide

## Production Issues

### Invalid Host Header (192.168.x.x)
**Symptom:**
Accessing the application via IP address or custom domain returns:
> {"detail": "Invalid host header: 192.168.88.120. Allowed: ['localhost', '127.0.0.1']"}

**Cause:**
In production mode (`DEBUG=False`), RackPlane enforces strict Host header validation to prevent HTTP Host Header attacks. It intentionally **does not** auto-add detected IPs (like gateway or HOST_IP) to the allowed list, but only warns about them.

**Solution:**
Add your server's IP or domain to the `ALLOWED_HOSTS` environment variable in `.env` (passed at runtime).

```bash
# In .env file
ALLOWED_HOSTS=["localhost", "127.0.0.1", "backend", "192.168.88.120"]
```
*Note: Ensure valid JSON format. If using docker-compose, recreate the container (`up -d`) to apply.*

### ModuleNotFoundError: No module named 'anthropic'
**Symptom:**
Backend fails to start or crashes when using AI features with:
> ModuleNotFoundError: No module named 'anthropic'

**Cause:**
The default Docker build mode (`arg BUILD_MODE`) defaults to `oss` (Open Source), which uses `requirements-oss.txt`. The `anthropic` package is excluded from the OSS build to keep it lightweight.

**Solution:**
1. **Permanent:** Build with `BUILD_MODE=premium` or add `anthropic` to `requirements-oss.txt`.
2. **Hotfix (Production):** 
   ```bash
   docker compose exec backend pip install anthropic
   docker compose restart backend
   ```

### Storage Container Migration Fails (Unique Violation)
**Symptom:**
Running `migrate_asset_boxes_to_storage_containers.py` fails with:
> duplicate key value violates unique constraint "storage_containers_pkey"

**Cause:**
The PostgreSQL primary key sequence (`storage_containers_id_seq`) is out of sync with the table data (likely due to manual inserts or restored backups).

**Solution:**
Reset the sequence to the maximum ID:
```bash
docker compose exec db psql -U dcms -d datacenter_inventory -c "SELECT setval('storage_containers_id_seq', (SELECT MAX(id) FROM storage_containers));"
```
Then re-run the migration script.

#
## 4. On-Prem Production Server Fixes

**Scenario:** On-prem standalone server (`192.168.88.120`) showing "This container is empty" or broken links.

**Steps to Fix:**

1.  **Update Frontend:** The frontend code contained bugs (interpolation errors and legacy links). The fixed image has been pushed to the registry.
    ```bash
    # On the On-Prem server:
    git fetch
    git checkout fix/production-storage-ui
    docker compose build frontend
    docker compose up -d frontend
    ```
    *Validation:* Refresh the page. "This container is empty" should typically disappear if data exists, or use correct grammar. Links to storage containers should be functional.

2.  **Run Migration (if missing):**
    If the data is old (Asset Boxes) and not yet migrated to StorageContainers:
    ```bash
    # Run migration
    docker compose exec backend python3 scripts/migrate_asset_boxes_to_storage_containers.py --all
    ```

3.  **Invalid Host Header:**
    Ensure `.env` has the correct IP:
    ```bash
    ALLOWED_HOSTS='["localhost", "127.0.0.1", "backend", "192.168.88.120"]'
    docker compose up -d backend
    ```
