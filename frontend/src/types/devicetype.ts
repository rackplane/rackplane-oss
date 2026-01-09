/**
 * TypeScript types for NetBox Device Type Library integration
 */

/**
 * List of manufacturers response
 */
export interface ManufacturerListResponse {
  manufacturers: string[];
  total: number;
}

/**
 * Summary of a device type without full YAML data
 */
export interface DeviceTypeSummary {
  slug: string;
  name: string;
  manufacturer: string;
}

/**
 * List of device types response
 */
export interface DeviceTypeListResponse {
  devices: DeviceTypeSummary[];
  total: number;
  manufacturer: string;
}

/**
 * Detailed device type information
 */
export interface DeviceTypeDetail {
  manufacturer: string;
  slug: string;
  model: string;
  u_height?: number;
  weight?: number;
  is_full_depth?: boolean;
  specifications: Record<string, any>;
  asset_type: string;
}

/**
 * Request to import a device type to VendorSKU
 */
export interface DeviceTypeImportRequest {
  manufacturer: string;
  slug: string;
}

/**
 * VendorSKU summary returned after import
 */
export interface VendorSKUSummary {
  id: number;
  vendor: string;
  sku: string;
  name: string;
  manufacturer: string;
  asset_type: string;
  specifications: Record<string, any>;
}

/**
 * Response after importing a device type
 */
export interface DeviceTypeImportResponse {
  success: boolean;
  message: string;
  sku_id?: number;
  sku?: VendorSKUSummary;
}

/**
 * Search request parameters
 */
export interface DeviceTypeSearchParams {
  query: string;
  manufacturer?: string;
  limit?: number;
}
