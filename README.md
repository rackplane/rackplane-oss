# RackPlane

[![CI](https://github.com/rackplane/rackplane-oss/actions/workflows/ci.yml/badge.svg)](https://github.com/rackplane/rackplane-oss/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/rackplane/rackplane-oss/branch/main/graph/badge.svg)](https://codecov.io/gh/rackplane/rackplane-oss)
[![License](https://img.shields.io/badge/License-AGPL--3.0-green.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

**Open Source Datacenter Hardware and Inventory Management**

## Overview

RackPlane is a comprehensive, real-time management platform for all physical assets within complex, multi-site datacenter environments. Built with modern technologies and a multi-tenant SaaS architecture, it provides complete lifecycle tracking, predictive maintenance, capacity management, and workflow automation with tiered subscription features.

**Deployment Options:**
- **Self-Hosted**: Full control, run on your infrastructure
- **RackPlane Cloud**: Managed SaaS at [rackplane.com](https://rackplane.com) with central services

**Key Capabilities:**
- **Tiered subscription model** - Community, Starter, Pro, and MSP plans
- **Real-time inventory tracking** with counters
- **Stock management** with automatic storage assignment
- **Port-to-port cable connections** - Track network cables to specific switch ports
- **API access** - RESTful API with JWT authentication
- Location & capacity management (datacenter → room → rack → U-position)



### 1. Real-Time Inventory Tracking

**Asset Management:**
- Centralized database for servers, switches, storage, cables, PDUs, etc.
- Photo documentation with MinIO storage
- Custom asset types and fields
- Warranty expiration tracking
- Serial number management

### 2. Stock Management & Storage

**Automatic Storage Assignment:**
- Items automatically assigned to storage boxes on creation
- Storage container tracking with location support
- Low stock alerts
- Bulk assignment via API or script
- Lifecycle management - automatic status changes on deployment
- Stock summaries by type, location, and container

### 3. Port-to-Port Cable Connections

**Network Port Management:**
- Track network ports on switches, routers, and servers
- Port templates for rapid device setup (Cisco, Arista, etc.)
- Port types: RJ45, SFP, SFP+, QSFP, QSFP-DD, Console, USB
- Speed and PoE configuration
- Port status tracking (active/inactive/up/down)

**Cable Connections:**
- Connect cables to specific ports (not just devices)
- Automatic deployment from storage when connected
- Cable type support: DAC, fiber, ethernet, power
- Connection history and audit trail

### 4. API Access & Authentication

**RESTful API:**
- Full CRUD operations on all resources
- JWT authentication with refresh tokens
- API key authentication for services
- Swagger/OpenAPI documentation at `/api/docs`
- Rate limiting and quota management

**Personal Access Tokens:**
- Scope-based permissions
- API key generation per tenant

### 5. Location Management

**Hierarchical Location Tracking:**
- Datacenter → Room → Rack → U-position
- Precise asset placement with visual rack diagrams
- Storage container locations

## Quick Start Installation

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git**
- **4GB RAM** minimum (8GB recommended)
- **10GB disk space**

### Installation Steps

#### Step 1: Clone Repository

```bash
git clone https://github.com/rackplane/rackplane-oss.git
cd rackplane
```

#### Step 2: Configure Environment

```bash
# Copy the example environment file
cp env.example .env

# Edit the environment file (optional - defaults work for local development)
nano .env
```

**Important Environment Variables:**
- `SECRET_KEY` - Generate with `openssl rand -hex 32`
- `DATABASE_URL` - PostgreSQL connection (default: `postgresql://rackplane:rackplane@db:5432/rackplane`)
- `SERVICES_DATABASE_URL` - Central services DB (optional, defaults to DATABASE_URL)
- `CORS_ORIGINS` - Configure for reverse proxy or IP access
- `ALLOWED_HOSTS` - Add your public IP or DNS that you will access the app through

**Default settings work for local development:**
- Database: PostgreSQL on port 5432
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Redis: Port 6379

#### Step 3: Start Services

```bash
# Start all services (database, backend, frontend, redis, celery, nginx)
docker compose up -d

# Check service status
docker compose ps
```

All services should show "Up" status.

#### Step 4: Initialize Database

```bash
# One command handles everything: migrations + bootstrap
docker compose exec backend python scripts/setup_database.py

# Or using Make:
make setup-db
```

This automatically:
- ✅ Runs all database migrations with constraint verification
- ✅ Runs regression tests
- ✅ Creates default data (admin user, asset types, etc.)
- ✅ Handles both fresh installations and upgrades seamlessly

**Default Admin Account:**
- Username: `admin`
- Password: `ChangeMe123!`
- **⚠️ Change this password immediately after first login!**

#### Step 5: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

#### Step 6: First Login

1. Open http://localhost:3000
2. Click "Login" (top right)
3. Enter default credentials
4. **Immediately change the password** in Settings

### Verification

```bash
# Check backend health
curl http://localhost:8000/health

# Check database connection
docker compose exec backend python -c "from app.core.database import engine; print('Database OK' if engine else 'Database Error')"

# Run test suite
docker compose exec backend pytest -v
```

## Project Structure

```
rackplane/
├── README.md                  # This file
├── LICENSE                    # AGPL-3.0 License
├── env.example                # Environment template
├── docker-compose.yml         # Docker orchestration
├── Makefile                   # Common commands
│
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── core/             # Core (config, database, auth, tenant, licensing)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # API endpoints
│   │   │   └── v1/           # API v1 routes
│   │   └── tasks/            # Celery background tasks
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest test suite
│   ├── scripts/              # Utility scripts
│   ├── cleanup_test_tenants.py  # Test data cleanup
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── PortList.tsx              # Network port management
│   │   │   ├── TemplateSelector.tsx      # Port template selector
│   │   │   ├── PortCreateModal.tsx       # Manual port creation
│   │   ├── pages/            # Page components
│   │   ├── config/           # Configuration
│   │   └── utils/            # Utilities
│   └── package.json          # Node dependencies
│
├── nginx/                    # Nginx reverse proxy
│   └── nginx.conf
│
└── docs/                    # Documentation
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    ├── API.md
    ├── MULTI_TENANCY.md
    ├── STOCK_MANAGEMENT.md
```

## Technology Stack

**Backend:**
- FastAPI (Python 3.13)
- PostgreSQL 17
- SQLAlchemy 2.0 (async support)
- Redis 7 (caching, sessions, Celery)
- Celery (background tasks)
- Alembic (schema migrations)
- JWT authentication (PyJWT)

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS (dark mode support)
- Axios (HTTP client)
- React Router v6

**Infrastructure:**
- Docker + Docker Compose
- Nginx (reverse proxy)

**Integrations:**
- MinIO (S3-compatible storage)

## Common Tasks

### Development

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Run tests
docker compose exec backend pytest -v

# Run specific test
docker compose exec backend pytest tests/test_network_ports_pytest.py -v

# Access backend shell
docker compose exec backend bash

# Access database
docker compose exec db psql -U rackplane -d rackplane
```

### Database Management

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback migration
docker compose exec backend alembic downgrade -1

# View migration history
docker compose exec backend alembic history

# Check current version
docker compose exec backend alembic current
```

### Cleanup & Maintenance

```bash
# Clean up test tenants
docker compose exec backend python cleanup_test_tenants.py

# Reset database (⚠️ Deletes all data)
docker compose down -v
docker compose up -d
docker compose exec backend python scripts/setup_database.py

# Update to latest code
git pull
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Production Deployment

```bash
# Build for production
docker compose -f docker-compose.prod.yml build

# Deploy to Kubernetes
kubectl apply -k k8s/overlays/production/

# Check deployment status
kubectl get pods -n rackplane

# View logs
kubectl logs -f deployment/rackplane-backend -n rackplane
```

## Configuration

### Security Best Practices

**Required for Production:**
1. **SECRET_KEY**: Generate with `openssl rand -hex 32`
2. **Database Password**: Use strong password, not default
3. **CORS_ORIGINS**: Restrict to your domain only
4. **SSL/TLS**: Enable HTTPS via reverse proxy
5. **Admin Password**: Change immediately after installation

**Optional Enhancements:**
- **MinIO**: For photo storage

### Reverse Proxy Setup

Example Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name rackplane.example.com;

    ssl_certificate /etc/ssl/certs/rackplane.crt;
    ssl_certificate_key /etc/ssl/private/rackplane.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Update `.env`:
```bash
CORS_ORIGINS=["https://rackplane.example.com"]
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# Check port availability
netstat -tuln | grep -E '3000|8000|5432|6379'

# View error logs
docker compose logs

# Restart specific service
docker compose restart backend
```

### Database Connection Errors

```bash
# Check database is running
docker compose ps db

# Test connection
docker compose exec db psql -U rackplane -d rackplane -c "SELECT 1"

# Check environment variables
docker compose exec backend env | grep DATABASE_URL
```

### Frontend Not Loading

```bash
# Check frontend logs
docker compose logs frontend

# Rebuild with no cache
docker compose build --no-cache frontend
docker compose up -d frontend

# Check API connectivity
curl http://localhost:8000/health
```

### Migration Errors

```bash
# Check current migration
docker compose exec backend alembic current

# Check for multiple heads
docker compose exec backend alembic heads

# Merge heads if needed
docker compose exec backend alembic merge heads -m "merge heads"
```

### Test Failures

```bash
# Run tests with verbose output
docker compose exec backend pytest -v --tb=short

# Run specific test file
docker compose exec backend pytest tests/test_network_ports_pytest.py -v

# Clean up test data
docker compose exec backend python cleanup_test_tenants.py
```

## Features in Subscription Version

For advanced features including Multi-tenancy, Cloud OCR, NetBox Sync, and Subscription Tiers, please see [PREMIUM_FEATURES.md](PREMIUM_FEATURES.md).

## Roadmap

**Initial Release**
Basic Features

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and patterns
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [API Documentation](docs/API.md) - REST API reference
- [Stock Management Guide](docs/STOCK_MANAGEMENT.md) - Inventory workflows
- [Port-to-Port Design](docs/PORT/) - Cable connection architecture

## Contributing

We welcome contributions! Please see our contributing guidelines.

**Development Workflow:**
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/rackplane/rackplane-oss/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rackplane/rackplane-oss/discussions)
- **Commercial Support**: Available for MSP tier customers

## License

GNU Affero General Public License v3.0 (AGPL-3.0) - See [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with modern technologies and best practices for datacenter infrastructure management.

**Special Thanks:**
- FastAPI framework
- SQLAlchemy ORM
- React ecosystem
- Docker community
- All contributors and users

---

**RackPlane** - Professional Datacenter Asset Management
