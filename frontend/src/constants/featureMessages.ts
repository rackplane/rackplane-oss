/**
 * Standardized messages for premium features across the application
 */

export const FEATURE_MESSAGES = {
  // Generic messages
  PREMIUM_REQUIRED: 'This feature requires a Premium subscription.',
  UPGRADE_TO_ACCESS: 'Please upgrade your plan to access this feature.',

  // Feature-specific messages
  CLOUD_OCR: 'Cloud OCR requires a Premium subscription. Please upgrade to access advanced OCR capabilities.',
  SKU_LOOKUP: 'SKU Catalog lookup requires a Premium subscription. Please upgrade to access vendor SKU matching.',
  VENDOR_INTEGRATIONS: 'Live vendor search requires a Premium subscription. Please upgrade to access real-time vendor API integration.',
  LABEL_PRINTING: 'Label printing requires a Premium subscription. Please upgrade to access this feature.',
  GLOBAL_CATALOG: 'Global catalog access requires a Premium subscription. Please upgrade to submit products to the shared catalog.',
  MULTI_TENANT: 'Multi-tenant management requires a Premium subscription. Please upgrade to manage multiple organizations.',
  ADMIN_PORTAL: 'Admin portal requires a Premium subscription. Please upgrade to access system-wide administrative features.',
} as const;

/**
 * Get a standardized premium feature error message
 */
export function getPremiumFeatureMessage(feature?: string): string {
  switch (feature) {
    case 'ocr_cloud':
    case 'cloud_ocr':
      return FEATURE_MESSAGES.CLOUD_OCR;
    case 'sku_lookup':
      return FEATURE_MESSAGES.SKU_LOOKUP;
    case 'vendor_integrations':
      return FEATURE_MESSAGES.VENDOR_INTEGRATIONS;
    case 'label_printing':
      return FEATURE_MESSAGES.LABEL_PRINTING;
    case 'global_catalog':
      return FEATURE_MESSAGES.GLOBAL_CATALOG;
    case 'multi_tenant':
      return FEATURE_MESSAGES.MULTI_TENANT;
    case 'admin_portal':
      return FEATURE_MESSAGES.ADMIN_PORTAL;
    default:
      return FEATURE_MESSAGES.PREMIUM_REQUIRED;
  }
}
