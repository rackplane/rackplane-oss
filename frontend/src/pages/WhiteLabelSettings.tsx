// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';

interface BrandingConfig {
    name: string;
    logoUrl: string | null;
    faviconUrl: string | null;
    primaryColor: string;
    secondaryColor: string;
    accentColor: string;
    fontFamily: string;
    customDomain: string | null;
}

interface VerticalPreset {
    name: string;
    display_name: string;
    description: string;
    terminology: Record<string, string>;
    default_features: Record<string, boolean>;
}

const WhiteLabelSettings: React.FC = () => {
    const { isTenantAdmin } = useAuth();
    const { refreshConfig, verticalPack, branding, terminology, verticalFeatures } = useWhiteLabel();

    // Branding state
    const [brandingData, setBrandingData] = useState<BrandingConfig>({
        name: 'RackPlane',
        logoUrl: null,
        faviconUrl: null,
        primaryColor: '#3b82f6',
        secondaryColor: '#1e40af',
        accentColor: '#60a5fa',
        fontFamily: 'Inter',
        customDomain: null,
    });

    // Terminology state
    const [terminologyData, setTerminologyData] = useState<Record<string, string>>({});

    // Vertical presets
    const [presets, setPresets] = useState<VerticalPreset[]>([]);
    const [selectedPreset, setSelectedPreset] = useState<string>('');
    const [overrideCustom, setOverrideCustom] = useState(false);

    // Feature flags
    const [features, setFeatures] = useState<Record<string, boolean>>({
        expiration_tracking: false,
        par_levels: false,
        lot_tracking: false,
        department_attribution: false,
    });

    // UI State
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'branding' | 'terminology' | 'features'>('branding');

    // Load data on mount
    useEffect(() => {
        fetchData();
        fetchPresets();
    }, []);

    // Update local state when context changes
    useEffect(() => {
        if (branding) {
            // Merge with defaults to ensure all fields are present
            setBrandingData((prev: BrandingConfig) => ({
                ...prev,
                name: branding.name || prev.name,
                logoUrl: branding.logoUrl ?? prev.logoUrl,
                faviconUrl: branding.faviconUrl ?? prev.faviconUrl,
                primaryColor: branding.primaryColor || prev.primaryColor,
                secondaryColor: branding.secondaryColor || prev.secondaryColor,
                accentColor: branding.accentColor || prev.accentColor,
                fontFamily: branding.fontFamily || prev.fontFamily,
                customDomain: branding.customDomain ?? prev.customDomain,
            }));
        }
        if (terminology) {
            setTerminologyData(terminology as unknown as Record<string, string>);
        }
        // Features are NOT synced from context here - they are managed by fetchData() 
        // to prevent context updates from overwriting user's local edits before save
        if (verticalPack) {
            setSelectedPreset(verticalPack);
        }
    }, [branding, terminology, verticalFeatures, verticalPack]);


    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_URL}/api/v1/whitelabel/config`);
            const config = response.data;

            if (config.branding) setBrandingData(config.branding);
            if (config.terminology) setTerminologyData(config.terminology);
            if (config.vertical_features) setFeatures(config.vertical_features);
            if (config.vertical_pack) setSelectedPreset(config.vertical_pack);

            setError(null);
        } catch (err: any) {
            setError('Failed to load white-label configuration');
            console.error('Error loading config:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchPresets = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/v1/whitelabel/presets`);
            setPresets(response.data.presets || []);
        } catch (err: any) {
            console.error('Error loading presets:', err);
        }
    };

    const handleSaveBranding = async () => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            await axios.patch(`${API_URL}/api/v1/whitelabel/branding`, brandingData);
            setSuccess('Branding saved successfully!');
            await refreshConfig();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save branding');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveTerminology = async () => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            await axios.patch(`${API_URL}/api/v1/whitelabel/terminology`, terminologyData);
            setSuccess('Terminology saved successfully!');
            await refreshConfig();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save terminology');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveFeatures = async () => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            await axios.patch(`${API_URL}/api/v1/whitelabel/vertical-features`, features);
            setSuccess('Features saved successfully!');
            await refreshConfig();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save features');
        } finally {
            setSaving(false);
        }
    };

    const handleApplyPreset = async () => {
        if (!selectedPreset) return;

        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            await axios.post(`${API_URL}/api/v1/whitelabel/presets/apply`, {
                vertical: selectedPreset,
                override_custom: overrideCustom,
            });
            setSuccess(`Applied ${selectedPreset} preset successfully!`);
            await fetchData();
            await refreshConfig();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to apply preset');
        } finally {
            setSaving(false);
        }
    };

    if (!isTenantAdmin) {
        return (
            <div className="p-6">
                <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
                    <strong>Permission Denied:</strong> Only tenant administrators can access white-label settings.
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-lg text-primary">Loading configuration...</div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-primary mb-6">White-Label Settings</h1>
            <p className="text-secondary mb-8">
                Customize the look and feel of your RackPlane instance, adjust terminology for your industry,
                and enable features specific to your vertical.
            </p>

            {/* Success/Error Messages */}
            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                    {error}
                </div>
            )}
            {success && (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
                    {success}
                </div>
            )}

            {/* Vertical Preset Selector */}
            <div className="card mb-6">
                <h2 className="text-xl font-semibold text-primary mb-4">🏢 Vertical Pack</h2>
                <p className="text-secondary mb-4">
                    Select a vertical preset to quickly configure terminology and features for your industry.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    {presets.map((preset) => (
                        <button
                            key={preset.name}
                            onClick={() => setSelectedPreset(preset.name)}
                            className={`p-4 rounded-lg border-2 text-left transition ${selectedPreset === preset.name
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
                                }`}
                        >
                            <h3 className="font-semibold text-primary">{preset.display_name}</h3>
                            <p className="text-sm text-secondary">{preset.description}</p>
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            checked={overrideCustom}
                            onChange={(e) => setOverrideCustom(e.target.checked)}
                            className="w-4 h-4 text-blue-600"
                        />
                        <span className="text-sm text-primary">Override custom terminology</span>
                    </label>
                    <button
                        onClick={handleApplyPreset}
                        disabled={saving || !selectedPreset}
                        className="btn-primary disabled:opacity-50"
                    >
                        {saving ? 'Applying...' : 'Apply Preset'}
                    </button>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-2 mb-6">
                <button
                    onClick={() => setActiveTab('branding')}
                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'branding'
                        ? 'bg-primary text-white'
                        : 'bg-button-secondary hover:bg-gray-300'
                        }`}
                >
                    🎨 Branding
                </button>
                <button
                    onClick={() => setActiveTab('terminology')}
                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'terminology'
                        ? 'bg-primary text-white'
                        : 'bg-button-secondary hover:bg-gray-300'
                        }`}
                >
                    📝 Terminology
                </button>
                <button
                    onClick={() => setActiveTab('features')}
                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'features'
                        ? 'bg-primary text-white'
                        : 'bg-button-secondary hover:bg-gray-300'
                        }`}
                >
                    ⚙️ Features
                </button>
            </div>

            {/* Branding Tab */}
            {activeTab === 'branding' && (
                <div className="card">
                    <h2 className="text-xl font-semibold text-primary mb-4">🎨 Branding Configuration</h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Product Name
                            </label>
                            <input
                                type="text"
                                value={brandingData.name}
                                onChange={(e) => setBrandingData({ ...brandingData, name: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                placeholder="RackPlane"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Font Family
                            </label>
                            <select
                                value={brandingData.fontFamily}
                                onChange={(e) => setBrandingData({ ...brandingData, fontFamily: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                            >
                                <option value="Inter">Inter</option>
                                <option value="Roboto">Roboto</option>
                                <option value="Open Sans">Open Sans</option>
                                <option value="Lato">Lato</option>
                                <option value="Poppins">Poppins</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Logo URL
                            </label>
                            <input
                                type="url"
                                value={brandingData.logoUrl || ''}
                                onChange={(e) => setBrandingData({ ...brandingData, logoUrl: e.target.value || null })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                placeholder="https://example.com/logo.png"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Favicon URL
                            </label>
                            <input
                                type="url"
                                value={brandingData.faviconUrl || ''}
                                onChange={(e) => setBrandingData({ ...brandingData, faviconUrl: e.target.value || null })}
                                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                placeholder="https://example.com/favicon.ico"
                            />
                        </div>
                    </div>

                    <h3 className="text-lg font-medium text-primary mb-3">Colors</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Primary Color
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="color"
                                    value={brandingData.primaryColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, primaryColor: e.target.value })}
                                    className="w-12 h-10 rounded cursor-pointer"
                                />
                                <input
                                    type="text"
                                    value={brandingData.primaryColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, primaryColor: e.target.value })}
                                    className="flex-1 px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Secondary Color
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="color"
                                    value={brandingData.secondaryColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, secondaryColor: e.target.value })}
                                    className="w-12 h-10 rounded cursor-pointer"
                                />
                                <input
                                    type="text"
                                    value={brandingData.secondaryColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, secondaryColor: e.target.value })}
                                    className="flex-1 px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-primary mb-1">
                                Accent Color
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="color"
                                    value={brandingData.accentColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, accentColor: e.target.value })}
                                    className="w-12 h-10 rounded cursor-pointer"
                                />
                                <input
                                    type="text"
                                    value={brandingData.accentColor}
                                    onChange={(e) => setBrandingData({ ...brandingData, accentColor: e.target.value })}
                                    className="flex-1 px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                />
                            </div>
                        </div>
                    </div>

                    <h3 className="text-lg font-medium text-primary mb-3">Custom Domain</h3>
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-primary mb-1">
                            Custom Domain (Optional)
                        </label>
                        <input
                            type="text"
                            value={brandingData.customDomain || ''}
                            onChange={(e) => setBrandingData({ ...brandingData, customDomain: e.target.value || null })}
                            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                            placeholder="inventory.yourcompany.com"
                        />
                        <p className="text-sm text-secondary mt-1">
                            Contact support to configure DNS for your custom domain.
                        </p>
                    </div>

                    <button
                        onClick={handleSaveBranding}
                        disabled={saving}
                        className="btn-primary disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Branding'}
                    </button>
                </div>
            )}

            {/* Terminology Tab */}
            {activeTab === 'terminology' && (
                <div className="card">
                    <h2 className="text-xl font-semibold text-primary mb-4">📝 Terminology Configuration</h2>
                    <p className="text-secondary mb-4">
                        Customize the labels used throughout the application to match your industry terminology.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        {[
                            { key: 'item', label: 'Item (singular)', description: 'e.g., Asset, Supply, Item' },
                            { key: 'items', label: 'Items (plural)', description: 'e.g., Assets, Supplies, Items' },
                            { key: 'location', label: 'Location (singular)', description: 'e.g., Datacenter, Facility, Warehouse' },
                            { key: 'locations', label: 'Locations (plural)', description: 'e.g., Datacenters, Facilities, Warehouses' },
                            { key: 'bin', label: 'Bin (singular)', description: 'e.g., Rack, Cabinet, Shelf' },
                            { key: 'bins', label: 'Bins (plural)', description: 'e.g., Racks, Cabinets, Shelves' },
                            { key: 'check_out', label: 'Check Out Action', description: 'e.g., Deploy, Dispense, Pick' },
                            { key: 'check_in', label: 'Check In Action', description: 'e.g., Return, Restock, Receive' },
                            { key: 'category', label: 'Category (singular)', description: 'e.g., Asset Type, Supply Category' },
                            { key: 'categories', label: 'Categories (plural)', description: 'e.g., Asset Types, Supply Categories' },
                        ].map(({ key, label, description }) => (
                            <div key={key}>
                                <label className="block text-sm font-medium text-primary mb-1">
                                    {label}
                                </label>
                                <input
                                    type="text"
                                    value={terminologyData[key] || ''}
                                    onChange={(e) => setTerminologyData({ ...terminologyData, [key]: e.target.value })}
                                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                                    placeholder={description}
                                />
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={handleSaveTerminology}
                        disabled={saving}
                        className="btn-primary disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Terminology'}
                    </button>
                </div>
            )}

            {/* Features Tab */}
            {activeTab === 'features' && (
                <div className="card">
                    <h2 className="text-xl font-semibold text-primary mb-4">⚙️ Vertical-Specific Features</h2>
                    <p className="text-secondary mb-4">
                        Enable or disable features based on your industry requirements.
                    </p>

                    <div className="space-y-4 mb-6">
                        {[
                            {
                                key: 'expiration_tracking',
                                label: 'Expiration Tracking',
                                description: 'Track expiration dates for perishable items and consumables'
                            },
                            {
                                key: 'par_levels',
                                label: 'PAR Levels',
                                description: 'Set periodic automatic replenishment thresholds for stock management'
                            },
                            {
                                key: 'lot_tracking',
                                label: 'Lot/Batch Tracking',
                                description: 'Track items by lot or batch number for recalls and traceability'
                            },
                            {
                                key: 'department_attribution',
                                label: 'Department Attribution',
                                description: 'Attribute inventory usage to specific departments or cost centers'
                            },
                        ].map(({ key, label, description }) => (
                            <label key={key} className="flex items-start gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={features[key] || false}
                                    onChange={(e) => setFeatures({ ...features, [key]: e.target.checked })}
                                    className="w-5 h-5 text-blue-600 mt-0.5"
                                />
                                <div>
                                    <span className="font-medium text-primary">{label}</span>
                                    <p className="text-sm text-secondary">{description}</p>
                                </div>
                            </label>
                        ))}
                    </div>

                    {/* Field Visibility Section */}
                    <h3 className="text-lg font-semibold text-primary mb-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                        📋 Asset Form Fields
                    </h3>
                    <p className="text-secondary mb-4">
                        Show or hide fields on the asset creation/edit form based on your industry needs.
                    </p>

                    <div className="space-y-4 mb-6">
                        {[
                            {
                                key: 'show_power_watts',
                                label: 'Power Consumption (Watts)',
                                description: 'Show power consumption field for electrical equipment'
                            },
                            {
                                key: 'show_warranty_info',
                                label: 'Warranty Information',
                                description: 'Show warranty start and expiration date fields'
                            },
                            {
                                key: 'show_hostname',
                                label: 'Hostname',
                                description: 'Show hostname field for network-connected devices'
                            },
                            {
                                key: 'show_rack_position',
                                label: 'Rack Position (Height U)',
                                description: 'Show height (U) and rack position fields for datacenter equipment'
                            },
                            {
                                key: 'show_datacenter_location',
                                label: 'Datacenter/Rack Location',
                                description: 'Show datacenter and rack dropdown selectors'
                            },
                            {
                                key: 'show_sku_lookup',
                                label: 'SKU Lookup',
                                description: 'Show SKU field with catalog lookup functionality'
                            },
                            {
                                key: 'show_loan_tracking',
                                label: 'Loan Tracking',
                                description: 'Show "Asset is on loan" checkbox and related fields'
                            },
                        ].map(({ key, label, description }) => (
                            <label key={key} className="flex items-start gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={features[key] ?? true}
                                    onChange={(e) => setFeatures({ ...features, [key]: e.target.checked })}
                                    className="w-5 h-5 text-blue-600 mt-0.5"
                                />
                                <div>
                                    <span className="font-medium text-primary">{label}</span>
                                    <p className="text-sm text-secondary">{description}</p>
                                </div>
                            </label>
                        ))}
                    </div>

                    <button
                        onClick={handleSaveFeatures}
                        disabled={saving}
                        className="btn-primary disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Features'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default WhiteLabelSettings;
