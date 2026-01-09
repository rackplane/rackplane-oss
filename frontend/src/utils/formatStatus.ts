// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Status display name mapping and formatting utility.
 * Converts internal status slugs (e.g., 'in_storage') to human-readable display names (e.g., 'In Storage').
 */

import { snakeCaseToTitleCase, deriveOptions } from './formatHelpers';

/**
 * Mapping of status slugs to display names.
 * This is the single source of truth for status labels.
 */
export const STATUS_LABELS: Record<string, string> = {
    // Common statuses
    received: 'Received',
    staging: 'Staging',
    in_storage: 'In Storage',
    deployed: 'Deployed',
    active: 'Active',
    maintenance: 'Maintenance',
    failed: 'Failed',
    rma: 'RMA',
    retired: 'Retired',
    decommissioned: 'Decommissioned',

    // Additional statuses that might exist
    pending: 'Pending',
    available: 'Available',
    in_use: 'In Use',
    reserved: 'Reserved',
    on_order: 'On Order',
    shipped: 'Shipped',
    returned: 'Returned',
    disposed: 'Disposed',
    lost: 'Lost',
    broken: 'Broken',
    testing: 'Testing',
    provisioning: 'Provisioning',
    offline: 'Offline',
    online: 'Online',
};

/**
 * Convert a status slug to a human-readable display name.
 * @param slug - The internal status slug (e.g., 'in_storage')
 * @returns The display name (e.g., 'In Storage')
 */
export function formatStatus(slug: string | null | undefined): string {
    if (!slug) return '-';

    const normalizedSlug = slug.toLowerCase().trim();

    // Check if we have an explicit mapping
    if (STATUS_LABELS[normalizedSlug]) {
        return STATUS_LABELS[normalizedSlug];
    }

    // Fallback: Convert snake_case to Title Case using shared helper
    return snakeCaseToTitleCase(normalizedSlug);
}

/**
 * Keys for the curated subset of statuses shown in dropdowns and filters.
 * Add or remove keys here to control which options appear in the UI.
 * The labels are derived from STATUS_LABELS to prevent drift.
 */
const STATUS_OPTION_KEYS: Array<keyof typeof STATUS_LABELS> = [
    'received',
    'staging',
    'in_storage',
    'deployed',
    'active',
    'maintenance',
    'failed',
    'rma',
    'retired',
    'decommissioned',
];

/**
 * Common status options for dropdowns.
 * Provides consistent value/label pairs for use in forms and filters.
 * Derived from STATUS_LABELS to ensure labels stay in sync.
 */
export const STATUS_OPTIONS = deriveOptions(STATUS_LABELS, STATUS_OPTION_KEYS);
