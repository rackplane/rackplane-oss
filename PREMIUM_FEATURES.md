# RackPlane Premium Features

RackPlane offers additional features for professional and enterprise use cases, available through our tiered subscription plans.

## 1. Multi-Tenant SaaS Architecture

**Tenant Isolation:**
- Shared database with complete tenant-level data isolation
- Tenant-scoped queries via SQLAlchemy filters
- JWT tokens carry tenant context automatically
- Super admin capabilities for cross-tenant management

**Central Services (services.rackplane.com):**
- Separate database for global catalog, licensing, and quota management
- API key authentication for customer instances
- Contributor program for MSP partners
- Early access code system

## 2. Subscription Tiers & Licensing

**Tier System:**
- **Community** (Free) - Basic asset management, built-in OCR
- **Starter** ($49/mo) - Cloud OCR (100 scans/mo), low stock alerts, label printing
- **Pro** ($149/mo) - Unlimited users, NetBox sync, API access, vendor SKU lookup, rack visualization
- **MSP** (Custom) - Multi-tenant, unlimited OCR, admin portal, white-label options

**License Activation:**
- JWT-based license tokens
- Feature gating based on subscription tier
- Stripe checkout integration
- Auto-provisioning of API keys on subscription

## 3. Cloud OCR & Document Processing

**Cloud OCR Service:**
- Extract asset data from labels, invoices, and photos
- Powered by services.rackplane.com
- Quota-based usage (tier-dependent)
- Correction submission for improved accuracy

**FS.com Invoice Parser:**
- Upload invoice PDFs to auto-populate assets
- Extract product IDs, quantities, and specifications
- Automatic catalog lookup and asset creation

## 4. Advanced Integrations

**NetBox Integration (Pro+):**
- Bidirectional Sync
- Automatic device import/export
- Rack and site synchronization
- IP address management integration
- Conflict resolution

**Global SKU Catalog (Pro+):**
- Shared catalog across all customers
- Import vendor SKUs directly into inventory

## 5. Predictive Maintenance

**AI-Powered Analysis:**
- Failure prediction based on historical patterns
- Proactive maintenance scheduling
- MTTR (Mean Time To Repair) tracking
- Parts inventory management

## 6. Workflow Automation

**Standard Operating Procedures:**
- MACs (Moves, Adds, Changes) workflows
- Deployment and decommissioning automation
- Approval workflows

## 7. Visualization & Monitoring

**Rack Visualization (Community):**
- Visual elevation diagrams
- Color-coded by asset type or status
- Drag-and-drop placement
- Multi-U device support

**Real-Time Capacity Monitoring (Pro+):**
- **Space**: U-position utilization and availability
- **Power**: kW consumption vs capacity
- **Cooling**: BTU/hr requirements
- Intelligent placement suggestions

**Environmental Monitoring:**
- **Sensor Integration**: Temperature and humidity tracking
- SNMP, Modbus, and HTTP sensor support
- Threshold-based alerting
- Environmental compliance reporting
- Asset-environment correlation

## 8. Reporting & Compliance

**Comprehensive Reports:**
- Asset utilization and capacity planning
- Power Usage Effectiveness (PUE)
- Financial reports (depreciation, inventory value)
- Stock level and low stock alerts
- Audit trails for compliance
- Export to Excel, CSV, PDF

## Feature Comparison

| Feature | Community | Starter | Pro | MSP |
|---------|-----------|---------|-----|-----|
| Basic Asset Management | ✅ | ✅ | ✅ | ✅ |
| Built-in OCR | ✅ | ✅ | ✅ | ✅ |
| Rack Visualization | ✅ | ✅ | ✅ | ✅ |
| Cloud OCR | ❌ | 100/mo | 500/mo | Unlimited |
| Warranty Lookup | ❌ | ✅ | ✅ | ✅ |
| Low Stock Alerts | ❌ | ✅ | ✅ | ✅ |
| Label Printing | ❌ | ✅ | ✅ | ✅ |
| Unlimited Users | ❌ | ❌ | ✅ | ✅ |
| NetBox Sync | ❌ | ❌ | ✅ | ✅ |
| API Access | ❌ | ❌ | ✅ | ✅ |
| Vendor SKU Lookup | ❌ | ❌ | ✅ | ✅ |
| Capacity Monitoring | ❌ | ❌ | ✅ | ✅ |
| Environmental Monitoring | ❌ | ❌ | ✅ | ✅ |
| Multi-Tenant | ❌ | ❌ | ❌ | ✅ |
| Admin Portal | ❌ | ❌ | ❌ | ✅ |

For more details on pricing and features, visit [rackplane.com](https://rackplane.com).
