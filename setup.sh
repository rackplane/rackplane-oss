#!/bin/bash
# RackPlane OSS Setup Script
# This script rebuilds containers, initializes the database, and starts all services
# Uses docker-compose.yml for OSS deployment (renamed from docker-compose-oss.yml by filter)

set -e  # Exit on any error

# Use standard compose file (filter renames docker-compose-oss.yml -> docker-compose.yml)
COMPOSE_FILE="docker-compose.yml"
COMPOSE_CMD="docker compose -f $COMPOSE_FILE"

# Auto-detect Host IP for ALLOWED_HOSTS
echo "🔍 Detecting Host IP..."
HOST_IP=$(hostname -I | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="127.0.0.1"
fi
export HOST_IP
echo "   Host IP: $HOST_IP"


echo "============================================================"
echo "RackPlane OSS - Complete Setup"
echo "============================================================"
echo "Using compose file: $COMPOSE_FILE"
echo ""

# Function to print colored output
print_step() {
    echo ""
    echo "===================================="
    echo ">>> $1"
    echo "===================================="
}

# Function to check if command succeeded
check_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1 failed!"
        exit 1
    fi
}

# Step 1: Stop and remove existing containers/volumes
print_step "Step 1: Cleaning up existing containers and volumes"
$COMPOSE_CMD down -v
check_status "Cleanup complete"

# Step 2: Rebuild containers
print_step "Step 2: Rebuilding Docker containers (no cache)"
$COMPOSE_CMD build --no-cache backend frontend
check_status "Containers rebuilt"

# Step 3: Start database and redis first
print_step "Step 3: Starting database and redis"
$COMPOSE_CMD up -d db redis
check_status "Database and Redis started"

# Wait for database to be healthy
echo "⏳ Waiting for database to be ready..."
for i in {1..30}; do
    if $COMPOSE_CMD exec -T db pg_isready -U dcms -d datacenter_inventory > /dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Database failed to start after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Step 3.5: Ensure database is completely clean
echo "🧹 Ensuring database is completely clean..."
# Stop backend and celery_worker if running (to release database connections)
echo "   Stopping backend and celery_worker..."
$COMPOSE_CMD stop backend celery_worker 2>/dev/null || true
# Terminate all remaining connections to the database
echo "   Terminating database connections..."
$COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'datacenter_inventory' AND pid <> pg_backend_pid();" 2>&1 | grep -v "pg_terminate_backend" || true
sleep 2
# Drop and recreate the entire database for a truly clean slate
echo "   Dropping database..."
if ! $COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "DROP DATABASE IF EXISTS datacenter_inventory;" 2>&1; then
    echo "   ⚠️  DROP DATABASE failed, trying with force..."
    $COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "UPDATE pg_database SET datallowconn = 'false' WHERE datname = 'datacenter_inventory';" 2>&1 || true
    $COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'datacenter_inventory';" 2>&1 || true
    sleep 1
    $COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "DROP DATABASE IF EXISTS datacenter_inventory;" 2>&1 || true
fi
echo "   Creating database..."
$COMPOSE_CMD exec -T db psql -U dcms -d postgres -c "CREATE DATABASE datacenter_inventory OWNER dcms;"
check_status "Database recreated"

# Step 4: Run bootstrap (without starting backend permanently)
print_step "Step 4: Running database bootstrap"
# Run bootstrap using a temporary container, bypassing entrypoint to avoid auto-migrations
$COMPOSE_CMD run --rm --no-deps --entrypoint="" backend python bootstrap.py
check_status "Bootstrap complete"

# Step 5: Run migrations
print_step "Step 5: Running database migrations"
$COMPOSE_CMD run --rm --no-deps --entrypoint="" backend alembic upgrade head
check_status "Migrations complete"

# Step 6: Start backend service
print_step "Step 6: Starting backend service"
$COMPOSE_CMD up -d backend
check_status "Backend service started"

# Step 7: Start all remaining services
print_step "Step 7: Starting all services"
$COMPOSE_CMD up -d
check_status "All services started"

# Step 7.5: Install frontend dependencies (needed after volume mounts)
print_step "Step 7.5: Installing frontend dependencies"
echo "⏳ Installing npm packages in frontend container..."
$COMPOSE_CMD exec -T frontend npm install
check_status "Frontend dependencies installed"

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be fully ready..."
sleep 10

# Step 8: Display status
print_step "Step 8: Service Status"
$COMPOSE_CMD ps

# Step 9: Display summary
echo ""
echo "============================================================"
echo "✅ RackPlane OSS Setup Complete!"
echo "============================================================"
echo ""
echo "Services are available at:"
echo "  🌐 Frontend:     http://$HOST_IP:3000"
echo "  🔧 Backend API:  http://$HOST_IP:8000"
echo "  📚 API Docs:     http://$HOST_IP:8000/api/docs"
echo "  📊 Grafana:      http://localhost:3001 (admin/admin)"
echo "  📈 Prometheus:   http://localhost:9091"
echo ""
echo "Default Login Credentials:"
echo "  Username: admin"
echo "  Password: ChangeMe123!"
echo ""
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo ""
echo "To view logs:     $COMPOSE_CMD logs -f"
echo "To stop services: $COMPOSE_CMD down"
echo "============================================================"
