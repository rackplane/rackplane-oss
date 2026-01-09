// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * WhiteLabelContext - Manages tenant-specific branding and terminology
 * 
 * This context provides:
 * 1. Terminology customization (t() function for translating UI terms)
 * 2. Branding configuration (colors, logos, fonts)
 * 3. Vertical pack features (expiration tracking, par levels, etc.)
 * 
 * Usage:
 *   const { t, branding, verticalFeatures } = useWhiteLabel();
 *   <h1>{t('items')}</h1>  // Shows "Assets", "Supplies", or "Items" based on tenant config
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from './AuthContext';

// Terminology keys that can be customized
interface Terminology {
    item: string;
    items: string;
    location: string;
    locations: string;
    bin: string;
    bins: string;
    check_out: string;
    check_in: string;
    category: string;
    categories: string;
    lifecycle: string;
    storage: string;
    stock: string;
    container: string;
    containers: string;
}

// Branding configuration
interface BrandingConfig {
    name: string | null;
    logoUrl: string | null;
    faviconUrl: string | null;
    primaryColor: string;
    secondaryColor: string;
    accentColor: string;
    fontFamily: string;
    customDomain: string | null;
}

// Vertical-specific features
interface VerticalFeatures {
    // Healthcare/warehouse features
    expirationTracking: boolean;
    parLevels: boolean;
    lotTracking: boolean;
    departmentAttribution: boolean;

    // Field visibility toggles (datacenter default = true)
    showPowerWatts: boolean;
    showWarrantyInfo: boolean;
    showHostname: boolean;
    showRackPosition: boolean;
    showDatacenterLocation: boolean;
    showSkuLookup: boolean;
    showLoanTracking: boolean;
}

// Complete white-label configuration
interface WhiteLabelConfig {
    tenantId: number | null;
    tenantName: string;
    verticalPack: 'datacenter' | 'healthcare' | 'warehouse';
    terminology: Terminology;
    branding: BrandingConfig;
    verticalFeatures: VerticalFeatures;
}

// Default datacenter terminology
const DEFAULT_TERMINOLOGY: Terminology = {
    item: 'Asset',
    items: 'Assets',
    location: 'Datacenter',
    locations: 'Datacenters',
    bin: 'Rack',
    bins: 'Racks',
    check_out: 'Deploy',
    check_in: 'Return',
    category: 'Asset Type',
    categories: 'Asset Types',
    lifecycle: 'Status',
    storage: 'Storage',
    stock: 'Inventory',
    container: 'Storage Container',
    containers: 'Storage Containers'
};

// Default branding
const DEFAULT_BRANDING: BrandingConfig = {
    name: null,
    logoUrl: null,
    faviconUrl: null,
    primaryColor: '#6366f1',
    secondaryColor: '#4f46e5',
    accentColor: '#818cf8',
    fontFamily: 'Inter',
    customDomain: null
};

// Default features (datacenter defaults to showing all fields)
const DEFAULT_FEATURES: VerticalFeatures = {
    // Healthcare/warehouse features (off for datacenter)
    expirationTracking: false,
    parLevels: false,
    lotTracking: false,
    departmentAttribution: false,

    // Field visibility (all on for datacenter)
    showPowerWatts: true,
    showWarrantyInfo: true,
    showHostname: true,
    showRackPosition: true,
    showDatacenterLocation: true,
    showSkuLookup: true,
    showLoanTracking: true
};

// Default config
const DEFAULT_CONFIG: WhiteLabelConfig = {
    tenantId: null,
    tenantName: 'RackPlane',
    verticalPack: 'datacenter',
    terminology: DEFAULT_TERMINOLOGY,
    branding: DEFAULT_BRANDING,
    verticalFeatures: DEFAULT_FEATURES
};

// Context type
interface WhiteLabelContextType {
    config: WhiteLabelConfig;
    isLoading: boolean;
    error: string | null;

    // Terminology helper - use this for all UI text
    t: (key: keyof Terminology) => string;

    // Convenience accessors
    terminology: Terminology;
    branding: BrandingConfig;
    verticalFeatures: VerticalFeatures;
    verticalPack: string;
    displayName: string;

    // Feature checks
    hasFeature: (feature: keyof VerticalFeatures) => boolean;

    // Reload configuration
    refreshConfig: () => Promise<void>;
}

const WhiteLabelContext = createContext<WhiteLabelContextType | undefined>(undefined);

export const useWhiteLabel = () => {
    const context = useContext(WhiteLabelContext);
    if (!context) {
        throw new Error('useWhiteLabel must be used within a WhiteLabelProvider');
    }
    return context;
};

interface WhiteLabelProviderProps {
    children: ReactNode;
}

export const WhiteLabelProvider: React.FC<WhiteLabelProviderProps> = ({ children }) => {
    const { isAuthenticated, token } = useAuth();
    const [config, setConfig] = useState<WhiteLabelConfig>(DEFAULT_CONFIG);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load cached config on mount
    useEffect(() => {
        const cached = localStorage.getItem('whitelabel_config');
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                // Basic validation before using
                if (parsed && parsed.terminology && parsed.branding) {
                    setConfig(parsed);
                    applyBranding(parsed.branding);
                }
            } catch (e) {
                console.warn('Failed to parse cached whitelabel config', e);
            }
        }
    }, []);

    // Fetch configuration from API
    const fetchConfig = useCallback(async () => {
        if (!isAuthenticated || !token) {
            // Reset to defaults when not authenticated
            setConfig(DEFAULT_CONFIG);
            return;
        }

        // Don't set loading true if we have cached config (background refresh)
        if (!localStorage.getItem('whitelabel_config')) {
            setIsLoading(true);
        }

        setError(null);

        try {
            const response = await axios.get(`${API_URL}/api/v1/whitelabel/config`);
            const data = response.data;

            // Map API response to our config structure
            const newConfig: WhiteLabelConfig = {
                tenantId: data.tenant_id,
                tenantName: data.tenant_name,
                verticalPack: data.vertical_pack || 'datacenter',
                terminology: {
                    item: data.terminology?.item || DEFAULT_TERMINOLOGY.item,
                    items: data.terminology?.items || DEFAULT_TERMINOLOGY.items,
                    location: data.terminology?.location || DEFAULT_TERMINOLOGY.location,
                    locations: data.terminology?.locations || DEFAULT_TERMINOLOGY.locations,
                    bin: data.terminology?.bin || DEFAULT_TERMINOLOGY.bin,
                    bins: data.terminology?.bins || DEFAULT_TERMINOLOGY.bins,
                    check_out: data.terminology?.check_out || DEFAULT_TERMINOLOGY.check_out,
                    check_in: data.terminology?.check_in || DEFAULT_TERMINOLOGY.check_in,
                    category: data.terminology?.category || DEFAULT_TERMINOLOGY.category,
                    categories: data.terminology?.categories || DEFAULT_TERMINOLOGY.categories,
                    lifecycle: data.terminology?.lifecycle || DEFAULT_TERMINOLOGY.lifecycle,
                    storage: data.terminology?.storage || DEFAULT_TERMINOLOGY.storage,
                    stock: data.terminology?.stock || DEFAULT_TERMINOLOGY.stock,
                    container: data.terminology?.container || DEFAULT_TERMINOLOGY.container,
                    containers: data.terminology?.containers || DEFAULT_TERMINOLOGY.containers
                },
                branding: {
                    name: data.branding?.name || null,
                    logoUrl: data.branding?.logo_url || null,
                    faviconUrl: data.branding?.favicon_url || null,
                    primaryColor: data.branding?.primary_color || DEFAULT_BRANDING.primaryColor,
                    secondaryColor: data.branding?.secondary_color || DEFAULT_BRANDING.secondaryColor,
                    accentColor: data.branding?.accent_color || DEFAULT_BRANDING.accentColor,
                    fontFamily: data.branding?.font_family || DEFAULT_BRANDING.fontFamily,
                    customDomain: data.branding?.custom_domain || null
                },
                verticalFeatures: DEFAULT_FEATURES // Initialize with defaults to satisfy type requirement
            };

            try {
                // Safely parse vertical features with error handling
                if (data.vertical_features) {
                    newConfig.verticalFeatures = {
                        expirationTracking: data.vertical_features.expiration_tracking ?? false,
                        parLevels: data.vertical_features.par_levels ?? false,
                        lotTracking: data.vertical_features.lot_tracking ?? false,
                        departmentAttribution: data.vertical_features.department_attribution ?? false,
                        showPowerWatts: data.vertical_features.show_power_watts ?? true,
                        showWarrantyInfo: data.vertical_features.show_warranty_info ?? true,
                        showHostname: data.vertical_features.show_hostname ?? true,
                        showRackPosition: data.vertical_features.show_rack_position ?? true,
                        showDatacenterLocation: data.vertical_features.show_datacenter_location ?? true,
                        showSkuLookup: data.vertical_features.show_sku_lookup ?? true,
                        showLoanTracking: data.vertical_features.show_loan_tracking ?? true
                    };
                }
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Unknown parsing error';
                console.error('Failed to parse vertical features configuration:', err);
                // Propagate error to context state so it can be monitored/displayed if needed
                setError(`Configuration Warning: Failed to parse vertical features (${errorMessage}). Using defaults.`);
            }


            // Only update if changed (deep comparison would be better but this is simple)
            // For now, just setting it is fine as React handles diffing
            setConfig(newConfig);

            // Cache the new config
            localStorage.setItem('whitelabel_config', JSON.stringify(newConfig));

            // Apply branding to CSS custom properties
            applyBranding(newConfig.branding);

        } catch (err: any) {
            console.error('Failed to fetch white-label config:', err);
            setError(err.response?.data?.detail || 'Failed to load configuration');

            // Critical fallback: If we encountered an error and satisfy no config condition (empty or invalid),
            // force revert to defaults to ensure the app UI doesn't break for the user.
            if (!config || !config.terminology) {
                console.warn('Reverting to default white-label configuration due to API failure');
                setConfig(DEFAULT_CONFIG);
                applyBranding(DEFAULT_BRANDING);
            }
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated, token]);

    // Apply branding to document CSS custom properties
    const applyBranding = (branding: BrandingConfig) => {
        const root = document.documentElement;

        // Set color CSS variables
        root.style.setProperty('--color-primary', branding.primaryColor);
        root.style.setProperty('--color-secondary', branding.secondaryColor);
        root.style.setProperty('--color-accent', branding.accentColor);
        root.style.setProperty('--font-family-brand', branding.fontFamily);

        // Update favicon if custom one is set
        if (branding.faviconUrl) {
            const existingFavicon = document.querySelector("link[rel~='icon']") as HTMLLinkElement;
            if (existingFavicon) {
                existingFavicon.href = branding.faviconUrl;
            }
        }

        // Update document title if custom name is set
        if (branding.name) {
            document.title = branding.name;
        }
    };

    // Fetch config when authentication changes
    useEffect(() => {
        fetchConfig();
    }, [fetchConfig]);

    // Terminology translation function
    const t = useCallback((key: keyof Terminology): string => {
        return config.terminology[key] || key;
    }, [config.terminology]);

    // Feature check function
    const hasFeature = useCallback((feature: keyof VerticalFeatures): boolean => {
        return config.verticalFeatures[feature] || false;
    }, [config.verticalFeatures]);

    // Get display name (custom branding name or default)
    const displayName = config.branding.name || 'RackPlane';

    const value: WhiteLabelContextType = {
        config,
        isLoading,
        error,
        t,
        terminology: config.terminology,
        branding: config.branding,
        verticalFeatures: config.verticalFeatures,
        verticalPack: config.verticalPack,
        displayName,
        hasFeature,
        refreshConfig: fetchConfig
    };

    return (
        <WhiteLabelContext.Provider value={value}>
            {children}
        </WhiteLabelContext.Provider>
    );
};

// Export defaults for use in other components
export { DEFAULT_TERMINOLOGY, DEFAULT_BRANDING, DEFAULT_FEATURES };
export type { Terminology, BrandingConfig, VerticalFeatures, WhiteLabelConfig };
