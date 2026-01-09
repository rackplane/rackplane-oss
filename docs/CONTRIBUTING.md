# RackPlane Documentation Site

This directory contains the source files for the RackPlane documentation site at [docs.rackplane.com](https://docs.rackplane.com).

## Structure

```
docs/
├── mkdocs.yml           # MkDocs configuration
├── README.md            # Documentation home page
├── guides/              # Getting started and setup guides
│   ├── GETTING_STARTED.md
│   ├── MULTI_TENANT_ONBOARDING.md
│   ├── LOCATION_SETUP.md
│   └── LABEL_PRINTING.md
├── training/            # In-depth training materials
│   ├── ASSET_MANAGEMENT.md
│   ├── WHITE_LABEL.md
│   ├── ADMINISTRATOR_GUIDE.md
│   ├── HEALTHCARE_VERTICAL.md
│   ├── WAREHOUSE_VERTICAL.md
│   ├── NETWORK_PORTS.md
│   └── REPORTS.md
├── api/                 # API reference documentation
│   ├── API_REFERENCE.md
│   ├── ASSETS_API.md
│   ├── LOCATIONS_API.md
│   ├── USERS_API.md
│   └── VERSION_API.md
├── operations/          # DevOps and operations guides
│   ├── DEPLOYMENT.md
│   ├── BACKUP_GUIDE.md
│   └── NETBOX_SETUP.md
└── assets/              # Images, logos, etc.
    ├── logo.png
    └── favicon.ico
```

## Building Locally

### Prerequisites

```bash
pip install mkdocs-material mkdocs-minify-plugin
```

### Serve Locally

```bash
cd docs
mkdocs serve
```

Open http://localhost:8000 to preview.

### Build Static Site

```bash
mkdocs build
```

Generated site will be in `site/` directory.

## Deploying to GitHub Pages

### Option 1: GitHub Actions (Recommended)

The docs are automatically built and deployed on push to main branch via GitHub Actions.

See `.github/workflows/docs.yml`.

### Option 2: Manual Deploy

```bash
mkdocs gh-deploy --force
```

This builds and pushes to the `gh-pages` branch.

## Contributing

1. Edit Markdown files in the appropriate directory
2. Preview locally with `mkdocs serve`
3. Submit a pull request
4. Docs auto-deploy when PR is merged

## Style Guide

- Use proper heading hierarchy (# → ## → ###)
- Include code examples where relevant
- Use admonitions for tips, warnings, notes:
  ```markdown
  !!! tip
      This is a helpful tip.
  
  !!! warning
      Be careful about this.
  ```
- Use tables for comparisons
- Include ASCII diagrams for concepts

## Industry Verticals

The docs cover three main industry verticals:

| Vertical | Directory | Key Pages |
|----------|-----------|-----------|
| **Datacenter** | Default | GETTING_STARTED.md, ASSET_MANAGEMENT.md |
| **Healthcare** | training/ | HEALTHCARE_VERTICAL.md |
| **Warehouse** | training/ | WAREHOUSE_VERTICAL.md |

## Contact

- **Documentation Issues**: [GitHub Issues](https://github.com/rackplane/docs/issues)
- **Content Suggestions**: docs@rackplane.com
- **Technical Support**: support@rackplane.com
