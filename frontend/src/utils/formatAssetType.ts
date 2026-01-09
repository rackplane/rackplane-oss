// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Utility function to format asset type slugs (e.g., "dac_cable") 
 * into human-readable display names (e.g., "DAC Cable").
 */

import { snakeCaseToTitleCase, deriveOptions } from './formatHelpers';

/**
 * Mapping of asset type slugs to display names.
 * This is the single source of truth for asset type labels.
 */
export const ASSET_TYPE_LABELS: Record<string, string> = {
    // Servers & Compute
    server: 'Server',
    blade_server: 'Blade Server',
    gpu: 'GPU',
    cpu: 'CPU',
    nic: 'NIC',
    memory: 'Memory',

    // Storage
    storage: 'Storage',
    ssd: 'SSD',
    hdd: 'HDD',
    nvme: 'NVMe',

    // Network Devices
    switch: 'Switch',
    network_switch: 'Network Switch',
    router: 'Router',
    firewall: 'Firewall',
    load_balancer: 'Load Balancer',

    // Power
    pdu: 'PDU',
    ups: 'UPS',
    power_strip: 'Power Strip',

    // Cables
    cable: 'Cable',
    dac_cable: 'DAC Cable',
    aoc_cable: 'AOC Cable',
    fiber_cable: 'Fiber Cable',
    ethernet_cable: 'Ethernet Cable',
    network_cable: 'Network Cable',
    electrical_cable: 'Electrical Cable',
    power_cable: 'Power Cable',

    // Transceivers
    transceiver: 'Transceiver',
    optical_transceiver: 'Optical Transceiver',
    copper_transceiver: 'Copper Transceiver',

    // Infrastructure
    patch_panel: 'Patch Panel',
    rack: 'Rack',
    enclosure: 'Enclosure',
    chassis: 'Chassis',

    // Other
    other: 'Other',
    unknown: 'Unknown',
};

/**
 * Formats an asset type slug into a human-readable display name.
 * 
 * @param slug - The internal asset type slug (e.g., "dac_cable")
 * @returns The formatted display name (e.g., "DAC Cable")
 * 
 * @example
 * formatAssetType('dac_cable') // Returns "DAC Cable"
 * formatAssetType('optical_transceiver') // Returns "Optical Transceiver"
 * formatAssetType(null) // Returns "-"
 */
export function formatAssetType(slug: string | null | undefined): string {
    if (!slug) return '-';

    const normalizedSlug = slug.toLowerCase().trim();

    // Check if we have an explicit mapping
    if (ASSET_TYPE_LABELS[normalizedSlug]) {
        return ASSET_TYPE_LABELS[normalizedSlug];
    }

    // Fallback: Convert snake_case to Title Case using shared helper
    return snakeCaseToTitleCase(normalizedSlug);
}

/**
 * Keys for the curated subset of asset types shown in dropdowns and filters.
 * Add or remove keys here to control which options appear in the UI.
 * The labels are derived from ASSET_TYPE_LABELS to prevent drift.
 */
const ASSET_TYPE_OPTION_KEYS: Array<keyof typeof ASSET_TYPE_LABELS> = [
    'server',
    'switch',
    'router',
    'storage',
    'pdu',
    'ups',
    'dac_cable',
    'aoc_cable',
    'fiber_cable',
    'ethernet_cable',
    'transceiver',
    'optical_transceiver',
    'nic',
    'gpu',
    'memory',
    'cpu',
    'ssd',
    'hdd',
    'patch_panel',
    'other',
];

/**
 * List of common asset types for use in dropdowns and filters.
 * Each entry has a value (slug) and label (display name).
 * Derived from ASSET_TYPE_LABELS to ensure labels stay in sync.
 */
export const ASSET_TYPE_OPTIONS = deriveOptions(ASSET_TYPE_LABELS, ASSET_TYPE_OPTION_KEYS);
