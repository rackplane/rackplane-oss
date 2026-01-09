// Navigation configuration - OSS Version
// Defines all navigation items organized into dropdown groups
// Premium features (NetBox, Service Contracts, Tenant Management) are excluded

export interface NavItem {
    id: string;
    label: string;
    path: string;
    icon?: string;
    requiresSuperAdmin?: boolean;
    requiresTenantAdmin?: boolean;
    requiresAuth?: boolean;
    premiumOnly?: boolean;
    category?: 'core' | 'tools' | 'admin';
    group?: 'core' | 'inventory' | 'operations' | 'tools' | 'data' | 'admin';
}

// Navigation group definitions for dropdown menus
export interface NavGroup {
    id: string;
    label: string;
    icon: string;
}

export const NAV_GROUPS: NavGroup[] = [
    { id: 'inventory', label: 'Inventory', icon: '📦' },
    { id: 'operations', label: 'Operations', icon: '🏭' },
    { id: 'tools', label: 'Tools', icon: '🛠️' },
    { id: 'data', label: 'Data', icon: '📊' },
    { id: 'admin', label: 'Admin', icon: '👤' },
];

// All available navigation items - OSS Version
export const ALL_NAV_ITEMS: NavItem[] = [
    // Core navigation items (always visible in top bar)
    { id: 'dashboard', label: 'Dashboard', path: '/', icon: '🏠', category: 'core', group: 'core' },

    // Inventory group - consolidated inventory management
    { id: 'inventory', label: 'Assets', path: '/assets', icon: '📦', category: 'core', group: 'inventory' },
    { id: 'storage', label: 'Storage', path: '/storage', icon: '🗄️', category: 'core', group: 'inventory' },
    { id: 'stock', label: 'Stock Status', path: '/stock', icon: '📊', category: 'core', group: 'inventory' },

    // Operations group
    { id: 'maintenance', label: 'Maintenance', path: '/maintenance', icon: '🔧', category: 'core', group: 'operations' },
    // Service Contracts removed for OSS
    { id: 'reports', label: 'Reports', path: '/reports', icon: '📈', category: 'core', group: 'operations' },

    // Tools group
    { id: 'locations', label: 'Locations', path: '/locations', icon: '📍', category: 'tools', group: 'tools' },
    { id: 'racks', label: 'Rack Visualizations', path: '/racks', icon: '🗄️', category: 'tools', group: 'tools' },
    { id: 'asset-types', label: 'Asset Types', path: '/asset-types', icon: '🏷️', category: 'tools', group: 'tools' },
    { id: 'port-templates', label: 'Port Templates', path: '/port-templates', icon: '📋', category: 'tools', group: 'tools' },
    { id: 'connections', label: 'Connections', path: '/connections', icon: '🔗', category: 'tools', group: 'tools' },
    { id: 'cable-assemblies', label: 'Cable Assemblies', path: '/cable-assemblies', icon: '📦', category: 'tools', group: 'tools' },
    { id: 'mobile', label: 'Mobile App', path: '/mobile', icon: '📱', category: 'tools', group: 'tools' },

    // Data group
    { id: 'vendor-skus', label: 'SKU Catalog', path: '/vendor-skus', icon: '📋', category: 'tools', group: 'data' },
    { id: 'catalog-submissions', label: 'Catalog Submissions', path: '/catalog-submissions', icon: '☁️', category: 'tools', group: 'data', requiresAuth: true },
    { id: 'backup', label: 'Backup', path: '/backup', icon: '💾', category: 'tools', group: 'data' },
    // NetBox removed for OSS

    // Admin group

    { id: 'users', label: 'User Management', path: '/users', icon: '👤', category: 'admin', group: 'admin', requiresAuth: true },
    // WhiteLabel removed for OSS
    { id: 'diagnostic', label: 'Diagnostic', path: '/diagnostic', icon: '🔧', category: 'admin', group: 'admin', requiresSuperAdmin: true },
];
