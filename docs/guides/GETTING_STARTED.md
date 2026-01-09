# Getting Started with RackPlane

## Welcome to RackPlane! 🎉

RackPlane is a flexible inventory and asset management platform that adapts to your industry. Whether you're managing a datacenter, hospital, warehouse, or something unique, this guide will help you get started.

---

## Table of Contents

1. [First Login](#first-login)
2. [Choose Your Industry Vertical](#choose-your-industry-vertical)
3. [Dashboard Overview by Vertical](#dashboard-overview-by-vertical)
4. [Initial Setup Workflows](#initial-setup-workflows)
5. [Adding Your First Items](#adding-your-first-items)
6. [Subscription Levels & Add-Ons](#subscription-levels--add-ons)
7. [Custom & Consulted Setup](#custom--consulted-setup)
8. [Getting Help](#getting-help)

---

## First Login

### Step 1: Access RackPlane

Navigate to your RackPlane instance:
- **Self-Hosted**: `http://your-server:3000`
- **RackPlane Cloud**: `https://app.rackplane.com`

### Step 2: Sign In

Enter your credentials:
- **Username**: Your assigned username or email
- **Password**: Your initial password

> ⚠️ **Important**: Change your password immediately after first login!

### Step 3: Change Password

1. Click your username in the top-right corner
2. Select **Settings**
3. Navigate to **Security** tab
4. Enter current password and new password
5. Click **Update Password**

---

## Choose Your Industry Vertical

RackPlane comes with pre-configured **vertical packs** for different industries. Your vertical determines the terminology, features, and default configuration.

### Available Verticals

| Vertical | Best For | Key Features |
|----------|----------|--------------|
| **🖥️ Datacenter** | IT infrastructure, data centers, MSPs | Rack visualization, power efficiency, network ports |
| **🏥 Healthcare** | Hospitals, clinics, medical supply | Expiration tracking, lot numbers, compliance |
| **📦 Warehouse** | Distribution, logistics, manufacturing | Bin locations, pick/pack, inventory counts |
| **🔧 Custom** | Unique industries | Contact us for tailored setup |

### Setting Your Vertical

**During Initial Setup:**
Your vertical was selected when your account was created. If you need to change it:

1. Navigate to **Settings** → **White-Label** → **Vertical Pack**
2. Select your industry from the dropdown
3. Choose whether to reset terminology and features
4. Click **Apply**

> 💡 **Tip**: Changing verticals updates terminology throughout the app (e.g., "Assets" → "Supplies" for Healthcare)

---

## Dashboard Overview by Vertical

The dashboard adapts to show information relevant to your industry.

### 🖥️ Datacenter Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  RackPlane - Datacenter Inventory Management                │
├─────────────────────────────────────────────────────────────┤
│  📊 Dashboard │ 📦 Assets │ 📍 Datacenters │ 🔌 Ports │ ⚡ Power │
├─────────────────────────────────────────────────────────────┤
│  Total Assets:     1,245    │  Active Racks:      48       │
│  Storage Items:      320    │  Power Usage:    145 kW      │
│  Warranty Expiring:   12    │  Network Ports:  2,400       │
└─────────────────────────────────────────────────────────────┘
```

**Navigation:**
| Section | Description |
|---------|-------------|
| **Dashboard** | Asset counts, capacity overview |
| **Assets** | Servers, switches, cables, transceivers |
| **Datacenters** | Datacenter → Room → Rack hierarchy |
| **Ports** | Network port management |
| **Power** | Power efficiency advisor (datacenter only) |
| **Stock** | Spare parts in storage |
| **Reports** | Capacity, utilization reports |

---

### 🏥 Healthcare Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  MedTrack - Medical Supply Management                       │
├─────────────────────────────────────────────────────────────┤
│  📊 Dashboard │ 💊 Supplies │ 🏥 Facilities │ ⏰ Expiring    │
├─────────────────────────────────────────────────────────────┤
│  Total Supplies:   8,450    │  Facilities:       12        │
│  Expiring (30d):      23    │  Expired:           2        │
│  Low Stock Alerts:    15    │  Dispensed Today: 147        │
└─────────────────────────────────────────────────────────────┘
```

**Navigation:**
| Section | Description |
|---------|-------------|
| **Dashboard** | Expiration alerts, stock levels |
| **Supplies** | Medical devices, medications, consumables |
| **Facilities** | Hospital → Department → Cabinet hierarchy |
| **Expiring** | Items expiring soon (FEFO view) |
| **Par Levels** | Minimum stock monitoring |
| **Lot Tracking** | Batch/lot number traceability |
| **Reports** | Expiration, waste analysis reports |

---

### 📦 Warehouse Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  StockFlow - Warehouse Inventory Management                 │
├─────────────────────────────────────────────────────────────┤
│  📊 Dashboard │ 📦 Items │ 🏢 Warehouses │ 📋 Picks │ 📊 Counts │
├─────────────────────────────────────────────────────────────┤
│  Total Items:     24,500    │  Bin Locations:   1,200      │
│  Low Stock:          45     │  Active Picks:       23      │
│  Received Today:    125     │  Shipped Today:     340      │
└─────────────────────────────────────────────────────────────┘
```

**Navigation:**
| Section | Description |
|---------|-------------|
| **Dashboard** | Inventory levels, activity metrics |
| **Items** | SKUs, products, components |
| **Warehouses** | Warehouse → Zone → Aisle → Bin hierarchy |
| **Picks** | Pick lists, fulfillment orders |
| **Receiving** | Inbound shipment processing |
| **Counts** | Cycle counts, inventory audits |
| **Reports** | Accuracy, velocity reports |

---

## Initial Setup Workflows

Follow the setup guide for your specific vertical:

### 🖥️ Datacenter Setup Workflow

```
Week 1: Foundation
├── Day 1-2: Create datacenters and rooms
├── Day 3-4: Add racks with U-positions
├── Day 5: Set up storage containers for spare parts
│
Week 2: Population
├── Day 1-3: Add major assets (servers, switches)
├── Day 4-5: Configure network ports
│
Week 3: Refinement
├── Add remaining assets (cables, transceivers)
├── Print asset labels
└── Train team members
```

**Detailed Steps:**
1. **Create Datacenters** - Settings → Locations → + Add Datacenter
2. **Add Rooms** (optional) - Subdivisions within datacenters
3. **Create Racks** - 42U standard, specify rows and positions
4. **Add Storage** - For spare cables, transceivers, etc.
5. **Import Assets** - CSV import or manual entry
6. **Configure Ports** - Define network ports on switches/servers
7. **Connect Cables** - Map cable connections between ports

📖 **Full Guide**: [Datacenter Setup Guide](LOCATION_SETUP.md)

---

### 🏥 Healthcare Setup Workflow

```
Week 1: Foundation
├── Day 1-2: Create facilities and departments
├── Day 3-4: Add storage cabinets and carts
├── Day 5: Configure expiration tracking settings
│
Week 2: Population
├── Day 1-3: Add supplies with lot numbers
├── Day 4-5: Set par levels for reorder points
│
Week 3: Refinement
├── Configure email alerts for expirations
├── Train staff on dispense/restock workflow
└── Set up compliance reporting
```

**Detailed Steps:**
1. **Create Facilities** - Settings → Locations → + Add Facility
2. **Add Departments** - ER, Pharmacy, OR, etc.
3. **Create Cabinets** - Medical supply storage locations
4. **Configure Expiration Alerts** - Settings → Plugins → Expiration Tracking
5. **Import Supplies** - Include lot numbers and expiration dates
6. **Set Par Levels** - Minimum stock thresholds per item
7. **Configure FEFO** - Enable First Expired, First Out picking

📖 **Full Guide**: [Healthcare Vertical Guide](../training/HEALTHCARE_VERTICAL.md)

---

### 📦 Warehouse Setup Workflow

```
Week 1: Foundation
├── Day 1-2: Create warehouses and zones
├── Day 3-4: Define bin location structure
├── Day 5: Set up receiving and shipping areas
│
Week 2: Population
├── Day 1-3: Import SKUs and inventory
├── Day 4-5: Assign items to bin locations
│
Week 3: Refinement
├── Configure pick workflows
├── Set reorder points
└── Train pickers and receivers
```

**Detailed Steps:**
1. **Create Warehouses** - Settings → Locations → + Add Warehouse
2. **Define Zones** - Fast-moving, bulk, returns, etc.
3. **Create Bin Locations** - Zone-Aisle-Shelf-Bin format
4. **Import Items** - SKUs with quantities
5. **Assign Locations** - Put items into bins
6. **Configure Par Levels** - Reorder points for purchasing
7. **Set Up Pick Process** - Single, batch, or wave picking

📖 **Full Guide**: [Warehouse Vertical Guide](../training/WAREHOUSE_VERTICAL.md)

---

### 🔧 Custom Vertical Setup

For industries not covered by standard verticals (aerospace, education, government, etc.), we offer customized setup.

**Custom Setup Includes:**
- Tailored terminology for your industry
- Custom asset types and categories
- Industry-specific reports
- Compliance configurations
- Integration with your existing systems
- On-site or remote training

➡️ **[Contact Us for Custom Setup](#custom--consulted-setup)**

---

## Adding Your First Items

Regardless of your vertical, adding items follows the same process:

### Method 1: Manual Entry

1. Navigate to your items page (Assets/Supplies/Items)
2. Click **+ Add** button
3. Select type/category
4. Fill in required fields
5. Assign location
6. Click **Create**

### Method 2: Barcode Scanning

1. Click the **📷 Scan** button
2. Point camera at barcode/QR code
3. Review extracted information
4. Complete any missing fields
5. Click **Create**

### Method 3: Bulk Import (CSV)

1. Navigate to **Import**
2. Download CSV template
3. Fill in your data
4. Upload and review
5. Confirm import

### Method 4: Vendor Import (Pro+)

Import directly from vendor invoices:
- **FS.com** - Network equipment
- **Mouser** - Electronic components
- More integrations available

---

## Subscription Levels & Add-Ons

### Subscription Tiers

| Feature | Community | Starter | Pro | MSP |
|---------|:---------:|:-------:|:---:|:---:|
| **Price** | Free | $49/mo | $149/mo | Custom |
| **Users** | 3 | 10 | Unlimited | Unlimited |
| **Items** | 500 | 5,000 | Unlimited | Unlimited |
| | | | | |
| Basic asset management | ✅ | ✅ | ✅ | ✅ |
| Mobile scanning | ✅ | ✅ | ✅ | ✅ |
| Reports & export | ✅ | ✅ | ✅ | ✅ |
| | | | | |
| Label printing | ❌ | ✅ | ✅ | ✅ |
| Low stock alerts | ❌ | ✅ | ✅ | ✅ |
| Cloud OCR | ❌ | 100/mo | 500/mo | Unlimited |
| | | | | |
| API access | ❌ | ❌ | ✅ | ✅ |
| NetBox integration | ❌ | ❌ | ✅ | ✅ |
| Vendor catalogs | ❌ | ❌ | ✅ | ✅ |
| Rack visualization | ❌ | ❌ | ✅ | ✅ |
| | | | | |
| Multi-tenant | ❌ | ❌ | ❌ | ✅ |
| White-label branding | ❌ | ❌ | ❌ | ✅ |
| Custom domain | ❌ | ❌ | ❌ | ✅ |
| Priority support | ❌ | ❌ | ❌ | ✅ |

### Available Add-Ons

Enhance your subscription with specialized add-ons:

| Add-On | Available On | Description |
|--------|--------------|-------------|
| **Healthcare Pack** | Starter+ | Expiration tracking, lot numbers, FEFO |
| **Warehouse Pack** | Starter+ | Pick/pack workflows, bin locations |
| **Compliance Pack** | Pro+ | Audit trails, compliance reports |
| **Integration Pack** | Pro+ | Additional API integrations |
| **Training Pack** | All tiers | 2 hours of personalized training |
| **Extra OCR** | Starter+ | Additional monthly OCR scans |

---

## Custom & Consulted Setup

### When to Consider Consulted Setup

- You have unique industry requirements
- Your terminology doesn't fit standard verticals
- You need integrations with existing systems
- You want migration from another system
- You require compliance configurations
- You need on-site training

### What's Included

**Discovery Session** (1 hour, free)
- Understand your requirements
- Recommend vertical and configuration
- Provide implementation timeline

**Consulted Setup** (Starting at $500)
- Custom vertical configuration
- Terminology customization
- Asset type setup
- Initial data import assistance
- User training session

**Enterprise Implementation** (Custom pricing)
- Full implementation management
- Custom integrations
- On-site training
- Dedicated support contact
- Ongoing consulting hours

### Contact Information

| Channel | Details |
|---------|---------|
| **📧 Sales** | sales@rackplane.com |
| **📧 Support** | support@rackplane.com |
| **📞 Phone** | +1 (555) 123-4567 |
| **💬 Live Chat** | Available on rackplane.com |
| **📅 Schedule Demo** | [Book a Demo](https://rackplane.com/demo) |

### Request a Consultation

Email us at **consulting@rackplane.com** with:

1. **Your Industry** - What type of organization?
2. **Size** - Approximate number of items to track?
3. **Current System** - What are you using now?
4. **Key Requirements** - Must-have features?
5. **Timeline** - When do you need to be live?

We'll respond within 1 business day to schedule a discovery call.

---

## Getting Help

### In-App Help
- Click the **?** icon for contextual help
- Tooltips appear on hover

### Documentation by Vertical

| Vertical | Getting Started | Full Guide |
|----------|-----------------|------------|
| Datacenter | This guide | [Datacenter Setup](LOCATION_SETUP.md) |
| Healthcare | This guide | [Healthcare Guide](../training/HEALTHCARE_VERTICAL.md) |
| Warehouse | This guide | [Warehouse Guide](../training/WAREHOUSE_VERTICAL.md) |
| Custom | Contact us | Provided during setup |

### Training Materials
- [Asset Management](../training/ASSET_MANAGEMENT.md) - Complete asset operations
- [White-Label Configuration](../training/WHITE_LABEL.md) - Branding customization
- [Administrator Guide](../training/ADMINISTRATOR_GUIDE.md) - User and tenant management

### Support Channels

| Priority | Channel | Response Time |
|----------|---------|---------------|
| Low | GitHub Discussions | 2-3 business days |
| Normal | Email (support@rackplane.com) | 1 business day |
| High | Live Chat (Pro+) | Within 4 hours |
| Critical | Phone (MSP only) | Within 1 hour |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus search bar |
| `n` | New item |
| `s` | Open scanner |
| `Esc` | Close modals |

---

## Next Steps

Based on your vertical:

### 🖥️ Datacenter
1. [Complete Location Setup](LOCATION_SETUP.md)
2. [Network Port Management](../training/NETWORK_PORTS.md)
3. [Cable Connections](../training/CABLE_CONNECTIONS.md)

### 🏥 Healthcare  
1. [Healthcare Vertical Guide](../training/HEALTHCARE_VERTICAL.md)
2. Configure expiration alerts
3. Set up par levels

### � Warehouse
1. [Warehouse Vertical Guide](../training/WAREHOUSE_VERTICAL.md)
2. Define bin locations
3. Configure pick workflows

### All Verticals
- [Asset Management Training](../training/ASSET_MANAGEMENT.md)
- [Label Printing Setup](LABEL_PRINTING.md)
- [White-Label Configuration](../training/WHITE_LABEL.md)

---

**Welcome to RackPlane!** 

You're now ready to take control of your inventory. Select your vertical, follow the setup workflow, and experience the power of industry-specific asset management.

Questions? Contact us at **support@rackplane.com** or schedule a **[free demo](https://rackplane.com/demo)**.
