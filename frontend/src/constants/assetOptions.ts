// Asset-related constants
// Extracted from Assets.tsx for reusability

// Limit for quick filter buttons to prevent UI clutter on smaller screens
export const MAX_QUICK_FILTER_BUTTONS = 5;

// Fiber connector options for cables and transceivers
export const FIBER_CONNECTOR_OPTIONS = [
    { value: 'LC', label: 'LC' },
    { value: 'SC', label: 'SC' },
    { value: 'FC', label: 'FC' },
    { value: 'ST', label: 'ST' },
    { value: 'MPO', label: 'MPO (Generic)' },
    { value: 'MPO-12', label: 'MPO-12' },
    { value: 'MPO-16', label: 'MPO-16' },
    { value: 'MPO-24', label: 'MPO-24' },
    { value: 'MTP', label: 'MTP (Generic)' },
    { value: 'MTP-8', label: 'MTP-8' },
    { value: 'MTP-12', label: 'MTP-12' },
    { value: 'MTP-16', label: 'MTP-16' },
    { value: 'MTP-24', label: 'MTP-24' },
] as const;

// DAC cable speed options
export const DAC_SPEED_OPTIONS = [
    { value: '10G', label: '10G' },
    { value: '25G', label: '25G' },
    { value: '40G', label: '40G' },
    { value: '100G', label: '100G' },
    { value: '200G', label: '200G' },
    { value: '400G', label: '400G' },
    { value: '800G', label: '800G' },
] as const;

// DAC connector options
export const DAC_CONNECTOR_OPTIONS = [
    { value: 'SFP+', label: 'SFP+' },
    { value: 'SFP28', label: 'SFP28' },
    { value: 'SFP56', label: 'SFP56' },
    { value: 'QSFP+', label: 'QSFP+' },
    { value: 'QSFP28', label: 'QSFP28' },
    { value: 'QSFP56', label: 'QSFP56' },
    { value: 'QSFP-DD', label: 'QSFP-DD' },
    { value: 'OSFP', label: 'OSFP' },
] as const;

// Fiber type options
export const FIBER_TYPE_OPTIONS = [
    { value: 'OM1', label: 'OM1 (62.5μm)' },
    { value: 'OM2', label: 'OM2 (50μm)' },
    { value: 'OM3', label: 'OM3 (50μm)' },
    { value: 'OM4', label: 'OM4 (50μm)' },
    { value: 'OM5', label: 'OM5 (50μm)' },
    { value: 'OS1', label: 'OS1 (9μm SM)' },
    { value: 'OS2', label: 'OS2 (9μm SM)' },
] as const;

// Ethernet cable category options
export const ETHERNET_CATEGORY_OPTIONS = [
    { value: 'Cat5', label: 'Cat5' },
    { value: 'Cat5e', label: 'Cat5e' },
    { value: 'Cat6', label: 'Cat6' },
    { value: 'Cat6a', label: 'Cat6a' },
    { value: 'Cat7', label: 'Cat7' },
    { value: 'Cat8', label: 'Cat8' },
] as const;

// Cable types that should not have min_stock_threshold
export const CABLE_ASSET_TYPES = [
    'dac_cable',
    'fiber_cable',
    'ethernet_cable',
    'network_cable',
    'power_cable',
    'aoc_cable',
] as const;

// Asset status options
// Asset status options
export const ASSET_STATUS_OPTIONS = [
    { value: 'received', label: 'Received' },
    { value: 'staging', label: 'Staging' },
    { value: 'in_storage', label: 'In Storage' },
    { value: 'deployed', label: 'Deployed' },
    { value: 'active', label: 'Active' },
    { value: 'in_maintenance', label: 'In Maintenance' },
    { value: 'maintenance', label: 'Maintenance' },
    { value: 'failed', label: 'Failed' },
    { value: 'decommissioned', label: 'Decommissioned' },
    { value: 'disposed', label: 'Disposed' },
    { value: 'rma', label: 'RMA' },
    { value: 'on_loan', label: 'On Loan' },
    { value: 'retired', label: 'Retired' },
] as const;
