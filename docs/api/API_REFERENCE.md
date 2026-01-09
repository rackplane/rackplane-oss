# API Reference

## Overview

RackPlane provides a RESTful API for all operations. This reference covers authentication, common patterns, and available endpoints.

---

## Base URL

| Environment | URL |
|-------------|-----|
| **Production** | `https://api.rackplane.com/api/v1` |
| **Self-Hosted** | `http://your-server:8000/api/v1` |
| **Development** | `http://localhost:8000/api/v1` |

---

## Authentication

### JWT Bearer Token

Most endpoints require authentication via JWT token:

```bash
curl -X GET https://api.rackplane.com/api/v1/assets \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Obtaining a Token

```bash
POST /api/v1/auth/login

{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Token Refresh

```bash
POST /api/v1/auth/refresh

Headers:
  Authorization: Bearer YOUR_CURRENT_TOKEN

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

## Common Response Formats

### Success Response

```json
{
  "data": { ... },
  "message": "Operation successful"
}
```

### List Response

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

### Error Response

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

---

## Pagination

List endpoints support pagination:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page` | 1 | Page number |
| `per_page` | 20 | Items per page (max 100) |
| `skip` | 0 | Number of items to skip |
| `limit` | 20 | Maximum items to return |

Example:
```bash
GET /api/v1/assets?page=2&per_page=50
```

---

## Filtering

Many endpoints support filtering:

```bash
# Filter by type
GET /api/v1/assets?type=server_device

# Filter by status
GET /api/v1/assets?status=active

# Filter by location
GET /api/v1/assets?datacenter_id=1&rack_id=5

# Combined filters
GET /api/v1/assets?type=switch_device&status=active&datacenter_id=1
```

---

## API Endpoints

### Core Resources

| Resource | Endpoint | Description |
|----------|----------|-------------|
| **Assets** | `/api/v1/assets` | [Asset CRUD operations](ASSETS_API.md) |
| **Locations** | `/api/v1/locations` | [Location management](LOCATIONS_API.md) |
| **Users** | `/api/v1/users` | [User management](USERS_API.md) |
| **Tenants** | `/api/v1/tenants` | Tenant management |

### Feature Resources

| Resource | Endpoint | Description |
|----------|----------|-------------|
| **Network Ports** | `/api/v1/network-ports` | Port management |
| **Cables** | `/api/v1/cables` | Cable connections |
| **Stock** | `/api/v1/stock` | Storage containers |
| **Reports** | `/api/v1/reports` | Report generation |

### Configuration

| Resource | Endpoint | Description |
|----------|----------|-------------|
| **White-Label** | `/api/v1/whitelabel` | Branding and terminology |
| **Plugins** | `/api/v1/plugins` | Plugin configuration |
| **Version** | `/api/v1/version` | [API version info](VERSION_API.md) |

---

## Rate Limiting

| Tier | Rate Limit |
|------|------------|
| Community | 100 requests/minute |
| Starter | 500 requests/minute |
| Pro | 2,000 requests/minute |
| MSP | Custom |

Rate limit headers:
```
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 498
X-RateLimit-Reset: 1640000000
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: `/api/docs`
- **ReDoc**: `/api/redoc`
- **OpenAPI JSON**: `/api/openapi.json`

---

## SDKs and Libraries

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- CLI Tool

---

## Next Steps

- [Assets API](ASSETS_API.md) - Asset CRUD operations
- [Locations API](LOCATIONS_API.md) - Location management
- [Users API](USERS_API.md) - User management
- [Version API](VERSION_API.md) - API versioning
