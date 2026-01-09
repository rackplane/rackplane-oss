#!/bin/bash
# Docker entrypoint script for RackPlane backend
# Auto-restores demo backup on first run (single-tenant Fly.io)

set -e

echo "🚀 RackPlane Backend Starting..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-rackplane}" -d "${POSTGRES_DB:-rackplane}" -c '\q' 2>/dev/null; do
  echo "   Database not ready, waiting..."
  sleep 1
done
echo "✅ Database ready"

# Run migrations
echo "📦 Running database migrations..."
alembic upgrade head || {
  echo "⚠️  Migration failed, continuing anyway..."
}

# Check if tenant 1 exists
echo "🔍 Checking for tenant 1..."
TENANT_EXISTS=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-rackplane}" -d "${POSTGRES_DB:-rackplane}" -tAc "SELECT COUNT(*) FROM tenants WHERE id = 1" 2>/dev/null || echo "0")

if [ "$TENANT_EXISTS" = "0" ] || [ -z "$TENANT_EXISTS" ]; then
  echo "📥 Tenant 1 not found, checking for demo backup..."
  
  BACKUP_FILE="/app/backend/fixtures/velocity_demo_backup.json"
  if [ -f "$BACKUP_FILE" ]; then
    echo "✅ Found backup file: $BACKUP_FILE"
    echo "🔄 Restoring demo data to tenant 1..."
    
    # Run restore script
    cd /app/backend
    python scripts/restore_demo_to_tenant1.py "$BACKUP_FILE" || {
      echo "⚠️  Restore failed, continuing anyway..."
    }
    
    echo "✅ Demo restore complete"
  else
    echo "ℹ️  No backup file found at $BACKUP_FILE"
    echo "   Skipping auto-restore. You can restore manually via:"
    echo "   python3 scripts/restore_demo_to_tenant1.py"
  fi
else
  echo "✅ Tenant 1 already exists, skipping auto-restore"
  echo "✅ Tenant 1 already exists, skipping auto-restore"
fi

# ALWAYS run bootstrap.py to ensure DB sequences are synced
# (I updated bootstrap.py to be idempotent and force-sync the sequence)
echo "🔧 Running system bootstrap (ensures DB sequences are in sync)..."
python bootstrap.py || {
    echo "⚠️  Bootstrap failed, continuing anyway..."
}

# Start the application
echo "🎯 Starting uvicorn..."
exec "$@"

