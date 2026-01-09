# NetBox Device Type Library Integration

## Overview

The NetBox Device Type Library integration allows you to automatically import device specifications from the community-maintained [netbox-community/devicetype-library](https://github.com/netbox-community/devicetype-library) repository on GitHub.

This library contains over 10,000 device type definitions from hundreds of manufacturers, including detailed specifications for:

- Physical dimensions (U height, weight, depth)
- Network interfaces and port counts
- Power requirements
- Console ports and management interfaces
- Module bays and expansion slots

## Benefits

- **Auto-populate asset fields**: When creating new assets, device specifications are automatically filled in
- **Accurate specifications**: Community-verified data from thousands of contributors
- **Comprehensive coverage**: Support for major manufacturers (Cisco, Dell, HP, Arista, Juniper, etc.)
- **Always up-to-date**: Data is fetched directly from GitHub, ensuring you have access to the latest device types

## How to Use

### Importing Device Types

1. Navigate to **Data → Vendor SKUs** in the main menu
2. Click the **"Import NetBox Device Types"** button (purple button in the toolbar)
3. In the import modal:
   - **Left column**: Select a manufacturer from the list
   - **Right column**: Browse available device types for that manufacturer
   - Use the search box to filter device types by model name
4. Click **"Import"** next to the device type you want to add
5. The device type will be added to your Vendor SKU catalog

### Using Imported Device Types

Once imported, device types appear in your Vendor SKU catalog with vendor name "NetBox Library". When creating a new asset:

1. Select the device type from the SKU lookup
2. Asset fields are automatically populated with:
   - Manufacturer
   - Model name
   - Asset type (switch, router, server, etc.)
   - Physical specifications (U height, weight)
   - Interface counts and details
   - Power requirements

## Features

### Smart Asset Type Detection

The system automatically infers the asset type based on:

- Model name keywords (e.g., "Catalyst" → switch, "ASR" → router)
- Interface counts (24+ ports usually indicate a switch)
- Device characteristics (many power ports → PDU)

Supported asset types:
- `switch` - Network switches
- `router` - Network routers
- `server` - Servers and compute devices
- `storage` - Storage arrays
- `pdu` - Power distribution units
- `ups` - Uninterruptible power supplies
- `firewall` - Security appliances
- `load_balancer` - Load balancers
- `console_server` - Console/terminal servers
- `other` - Unknown/other types

### Caching

Device type data is cached locally for 1 hour to improve performance and reduce GitHub API calls. The cache is stored in `/tmp/devicetype_cache/`.

To clear the cache (force refresh):
- Backend API: `DELETE /api/v1/netbox-devicetypes/cache`
- The cache automatically expires after 1 hour

### GitHub API Rate Limits

- **Without authentication**: 60 requests per hour
- **With GitHub token**: 5,000 requests per hour

To increase rate limits, add a GitHub personal access token to your environment:

```bash
GITHUB_TOKEN=your_github_token_here
```

Generate a token at: https://github.com/settings/tokens (no special scopes required for public repositories)

### GitHub Token Security

**Important Security Recommendations:**

- **Use read-only tokens**: The GitHub token only needs read access to public repositories. No write permissions are required.
- **Fine-grained personal access tokens (recommended)**: Use GitHub's [fine-grained tokens](https://github.com/settings/tokens?type=beta) with:
  - Repository access: **Public Repositories (read-only)**
  - Permissions: **Contents: Read-only**
- **Classic tokens**: If using classic tokens, **no scopes are required** for public repositories (leave all checkboxes unchecked)
- **Environment variables only**: Never commit tokens to version control. Always use environment variables or secrets management.
- **Token rotation**: Regularly rotate tokens as part of security best practices.

**Example: Creating a fine-grained token**
1. Visit https://github.com/settings/tokens?type=beta
2. Click **Generate new token**
3. Set token name: "RackPlane NetBox Integration (Read-Only)"
4. Repository access: **Public Repositories (read-only)**
5. Permissions → Repository permissions → Contents: **Read-only**
6. Click **Generate token**

## API Endpoints

For developers and automation, the following REST API endpoints are available:

### List Manufacturers

```http
GET /api/v1/netbox-devicetypes/manufacturers
```

Returns a list of all available manufacturers in the NetBox library.

**Response:**
```json
{
  "manufacturers": ["Cisco", "Dell", "HP", "Arista", ...],
  "total": 247
}
```

### List Device Types for Manufacturer

```http
GET /api/v1/netbox-devicetypes/manufacturers/{manufacturer}/devices?search=catalyst&limit=100&offset=0
```

Returns device types for a specific manufacturer with optional search and pagination.

**Response:**
```json
{
  "devices": [
    {
      "slug": "c9300-48uxm",
      "name": "Catalyst 9300 48Uxm",
      "manufacturer": "Cisco"
    }
  ],
  "total": 127,
  "manufacturer": "Cisco"
}
```

### Get Device Type Details

```http
GET /api/v1/netbox-devicetypes/manufacturers/{manufacturer}/devices/{slug}
```

Returns detailed specifications for a specific device type.

**Response:**
```json
{
  "manufacturer": "Cisco",
  "slug": "c9300-48uxm",
  "model": "Catalyst 9300-48UXM",
  "u_height": 1,
  "weight": 5.9,
  "is_full_depth": true,
  "specifications": {
    "network_ports": 48,
    "interface_details": {
      "1000base-t": 48,
      "10gbase-x-sfp+": 4
    },
    "power_ports": 2
  },
  "asset_type": "switch"
}
```

### Import Device Type

```http
POST /api/v1/netbox-devicetypes/import
Content-Type: application/json

{
  "manufacturer": "Cisco",
  "slug": "c9300-48uxm"
}
```

Imports a device type to your Vendor SKU catalog.

**Response:**
```json
{
  "success": true,
  "message": "Successfully imported Cisco Catalyst 9300-48UXM",
  "sku_id": 123,
  "sku": {
    "id": 123,
    "vendor": "NetBox Library",
    "sku": "netbox_cisco_c9300-48uxm",
    "name": "Catalyst 9300-48UXM",
    "manufacturer": "Cisco",
    "asset_type": "switch",
    "specifications": { ... }
  }
}
```

### Search Device Types

```http
POST /api/v1/netbox-devicetypes/search?query=catalyst&manufacturer=Cisco&limit=50
```

Search across all or specific manufacturers.

## Troubleshooting

### Rate Limit Errors

**Error:** "GitHub API rate limit exceeded"

**Solution:**
- Wait for the rate limit to reset (shown in error message)
- Add a GitHub personal access token to increase limits to 5,000/hour
- Use cached data (enabled by default)

### Import Conflicts

**Error:** "Device type already imported"

**Solution:**
The device type already exists in your catalog. You can find it by searching for the manufacturer or SKU in the Vendor SKUs page.

### Slow Loading

If the manufacturer or device list loads slowly:
- Data is being fetched from GitHub (first request)
- Subsequent requests will be faster due to caching
- Consider adding a GitHub token to improve performance

### Cache Issues

If you see stale data or want to force refresh:

```bash
curl -X DELETE http://localhost:8000/api/v1/netbox-devicetypes/cache \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration

Environment variables for customization:

```bash
# GitHub API token (optional, increases rate limits)
GITHUB_TOKEN=ghp_your_token_here

# Cache directory (default: /tmp/devicetype_cache)
DEVICETYPE_CACHE_DIR=/var/cache/devicetypes

# Cache TTL in seconds (default: 3600 = 1 hour)
DEVICETYPE_CACHE_TTL=7200
```

## Data Structure

Imported device types are stored as VendorSKU entries with:

- **Vendor**: "NetBox Library"
- **SKU**: `netbox_{manufacturer}_{slug}` (normalized, lowercase)
- **Part Number**: Original model name
- **Manufacturer**: Actual manufacturer (e.g., "Cisco", "Dell")
- **Asset Type**: Auto-detected type
- **Specifications**: JSON with all device details
- **Vendor URL**: Link to GitHub YAML file

## Best Practices

1. **Import before creating assets**: Import device types you frequently use so they're available during asset creation
2. **Use search**: With 10,000+ device types, search is the fastest way to find what you need
3. **Verify auto-detection**: The asset type is auto-detected but can be changed if incorrect
4. **Keep it organized**: Import device types as you need them rather than importing everything
5. **Check specifications**: Review the specifications JSON for detailed port layouts and requirements

## FAQ

**Q: Can I edit imported device types?**
A: Yes, imported device types become regular Vendor SKUs and can be edited like any other SKU entry.

**Q: Will this overwrite my existing assets?**
A: No, this only affects new asset creation. Existing assets are not modified.

**Q: How often is the NetBox library updated?**
A: The NetBox community library is actively maintained with daily contributions. Your imports will fetch the latest data from GitHub.

**Q: What if my device isn't in the library?**
A: You can:
1. Contribute it to the NetBox community library
2. Create a custom Vendor SKU entry manually
3. Use the FS.com or Mouser catalog search for similar devices

**Q: Does this require internet access?**
A: Yes, the initial import requires internet access to GitHub. Cached data is available offline for 1 hour.

## Related Features

- **Vendor SKU Catalog**: Manage product catalogs from multiple vendors
- **FS.com Integration**: Import products from FS.com catalog
- **Global Catalog**: Access RackPlane's curated product database
- **Asset Management**: Create and manage datacenter assets

## Support

For issues or questions:
- GitHub Issues: https://github.com/netbox-community/devicetype-library/issues
- RackPlane Documentation: /docs
- API Documentation: /api/docs

## Credits

Device type data is provided by the [NetBox Community](https://github.com/netbox-community/devicetype-library) under Apache 2.0 license.
