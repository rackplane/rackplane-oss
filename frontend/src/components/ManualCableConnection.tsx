// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * ManualCableConnection Component
 * 
 * Alternative to QR scanning - allows users to manually:
 * 1. Select two devices
 * 2. Select ports on each device
 * 3. Find compatible cables from inventory
 * 4. Create the connection
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import CompatibilityWarning, { CompatibilityResult } from './CompatibilityWarning';

interface Asset {
    id: number;
    asset_tag: string;
    asset_type: string;
    manufacturer?: string;
    model?: string;
}

interface NetworkPort {
    id: number;
    port_number: string;
    port_name?: string;
    port_label?: string;
    port_type: string;
    speed_mbps?: number;
    status?: string;
    installed_transceiver_id?: number;
}

interface CableAssembly {
    id: number;
    name: string;
    description?: string;
    status: string;
    fiber_cable_id: number;
    transceiver_a_id: number;
    transceiver_b_id: number;
    fiber_cable?: Asset;
    transceiver_a?: Asset;
    transceiver_b?: Asset;
}

interface ManualCableConnectionProps {
    onConnectionCreated?: () => void;
    initialAssetId?: number;
    initialPortId?: number;
}

const ManualCableConnection: React.FC<ManualCableConnectionProps> = ({
    onConnectionCreated,
    initialAssetId,
    initialPortId
}: ManualCableConnectionProps) => {
    // Device selection state
    const [deviceASearch, setDeviceASearch] = useState('');
    const [deviceBSearch, setDeviceBSearch] = useState('');
    const [deviceA, setDeviceA] = useState<Asset | null>(null);
    const [deviceB, setDeviceB] = useState<Asset | null>(null);
    const [searchResultsA, setSearchResultsA] = useState<Asset[]>([]);
    const [searchResultsB, setSearchResultsB] = useState<Asset[]>([]);
    const [showDropdownA, setShowDropdownA] = useState(false);
    const [showDropdownB, setShowDropdownB] = useState(false);

    // Port selection state
    const [portsA, setPortsA] = useState<NetworkPort[]>([]);
    const [portsB, setPortsB] = useState<NetworkPort[]>([]);
    const [selectedPortA, setSelectedPortA] = useState<NetworkPort | null>(null);
    const [selectedPortB, setSelectedPortB] = useState<NetworkPort | null>(null);
    const [loadingPortsA, setLoadingPortsA] = useState(false);
    const [loadingPortsB, setLoadingPortsB] = useState(false);

    // Cable selection state
    const [cableSearch, setCableSearch] = useState('');
    const [cableResults, setCableResults] = useState<Asset[]>([]);
    const [selectedCable, setSelectedCable] = useState<Asset | null>(null);
    const [showCableDropdown, setShowCableDropdown] = useState(false);

    // Cable Assembly mode state
    const [useAssemblyMode, setUseAssemblyMode] = useState(false);
    const [assemblySearch, setAssemblySearch] = useState('');
    const [assemblyResults, setAssemblyResults] = useState<CableAssembly[]>([]);
    const [selectedAssembly, setSelectedAssembly] = useState<CableAssembly | null>(null);
    const [showAssemblyDropdown, setShowAssemblyDropdown] = useState(false);

    // UI state
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<{
        message: string;
        cable_tag: string;
        device_a: string;
        port_a: string;
        device_b: string;
        port_b: string;
    } | null>(null);
    const [compatibilityResult, setCompatibilityResult] = useState<CompatibilityResult | null>(null);

    // Initial devices list (loaded on mount)
    const [initialDevices, setInitialDevices] = useState<Asset[]>([]);
    const [initialCables, setInitialCables] = useState<Asset[]>([]);

    // Load initial devices and cables on mount
    useEffect(() => {
        const loadInitialData = async () => {
            try {
                // Load recent devices (non-cables) that have ports configured
                const devicesRes = await axios.get(`${API_URL}/api/v1/assets/`, {
                    params: {
                        limit: 20,
                        exclude_types: 'dac_cable,ethernet_cable,fiber_cable,power_cable',
                        has_ports: true
                    }
                });
                const devices = devicesRes.data.assets || [];
                setInitialDevices(devices);

                // Handle initialAssetId prop
                if (initialAssetId) {
                    const found = devices.find((d: Asset) => d.id === initialAssetId);
                    if (found) {
                        selectDevice(found, 'A');
                    } else {
                        // Fetch if not in recent list
                        const res = await axios.get(`${API_URL}/api/v1/assets/${initialAssetId}`);
                        if (res.data) selectDevice(res.data, 'A');
                    }
                }

                // Load recent cables
                const cablesRes = await axios.get(`${API_URL}/api/v1/assets/`, {
                    params: {
                        limit: 20,
                        asset_type: 'dac_cable,ethernet_cable,fiber_cable'
                    }
                });
                setInitialCables(cablesRes.data.assets || []);
            } catch (err) {
                logger.error('Error loading initial data:', err);
            }
        };
        loadInitialData();
    }, [initialAssetId]);

    // Handle initialPortId when ports are loaded for Device A
    useEffect(() => {
        if (initialPortId && portsA.length > 0 && !selectedPortA) {
            const port = portsA.find((p: NetworkPort) => p.id === initialPortId);
            if (port) {
                setSelectedPortA(port);
                // Trigger cable search immediately when both ports are selected
                if (selectedPortB) {
                    searchCables('');
                }
            }
        }
    }, [initialPortId, portsA, selectedPortA, selectedPortB]);

    // Search for devices (or show initial list)
    const searchDevices = async (query: string, target: 'A' | 'B') => {
        if (query.length < 1) {
            // Show initial devices when empty
            if (target === 'A') {
                setSearchResultsA(initialDevices);
                setShowDropdownA(true);
            } else {
                setSearchResultsB(initialDevices);
                setShowDropdownB(true);
            }
            return;
        }

        try {
            const response = await axios.get(`${API_URL}/api/v1/assets/`, {
                params: {
                    search: query,
                    limit: 10,
                    // Exclude cable types and only show devices with ports
                    exclude_types: 'dac_cable,ethernet_cable,fiber_cable,power_cable',
                    has_ports: true
                }
            });
            const assets = response.data.assets || [];
            if (target === 'A') {
                setSearchResultsA(assets);
                setShowDropdownA(true);
            } else {
                setSearchResultsB(assets);
                setShowDropdownB(true);
            }
        } catch (err: any) {
            logger.error('Error searching devices:', err);
        }
    };

    // Fetch ports for a device
    const fetchPorts = async (deviceId: number, target: 'A' | 'B') => {
        const setLoading = target === 'A' ? setLoadingPortsA : setLoadingPortsB;
        const setPorts = target === 'A' ? setPortsA : setPortsB;

        try {
            setLoading(true);
            const response = await axios.get(`${API_URL}/api/v1/network-ports/`, {
                params: { asset_id: deviceId }
            });
            setPorts(response.data.ports || []);
        } catch (err: any) {
            logger.error('Error fetching ports:', err);
            setPorts([]);
        } finally {
            setLoading(false);
        }
    };

    // Search for cables (or show initial list)
    const searchCables = async (query: string) => {
        // Determine connector filter from selected ports
        let connectorType: string | undefined;
        const portType = selectedPortA?.port_type || selectedPortB?.port_type;

        if (portType) {
            const mapping: Record<string, string> = {
                'RJ45': 'rj45',
                'SFP': 'sfp',
                'SFP_PLUS': 'sfp+',
                'SFP28': 'sfp+', // Map to SFP+ for compatibility
                'QSFP': 'qsfp',
                'QSFP_PLUS': 'qsfp+',
                'QSFP28': 'qsfp28',
                'QSFP56': 'qsfp56',
                'QSFP112': 'qsfp28', // Map to QSFP28
                'QSFP_DD': 'qsfp-dd',
                'OSFP': 'osfp',
                'OSFP_FIN': 'osfp',
                'OSFP_FLT': 'osfp',
                'LC': 'lc',
                'SC': 'sc',
                'MPO': 'mpo'
            };
            connectorType = mapping[portType];
        }

        // If no query and no filter, show initials
        if (query.length < 1 && !connectorType) {
            setCableResults(initialCables);
            setShowCableDropdown(true);
            return;
        }

        try {
            // Priority 1: Search newer NetworkCable table
            const params: any = { limit: 20 };
            if (query.length > 0) params.search = query;
            if (connectorType) params.connector_type = connectorType;

            const ncRes = await axios.get(`${API_URL}/api/v1/network-cables/`, { params });
            const ncCables = ncRes.data.map((c: any) => ({
                id: c.id,
                asset_tag: c.name,
                asset_type: 'network_cable',
                manufacturer: c.manufacturer,
                model: c.model,
                ...c
            }));

            // Priority 2: Also search Assets table (legacy/general inventory) 
            // This is critical as most current cables are stored here
            // Make separate requests per type to support backends that don't handle comma-separated values
            const cableTypes = ['dac_cable', 'ethernet_cable', 'fiber_cable', 'power_cable'];
            const assetPromises = cableTypes.map(type =>
                axios.get(`${API_URL}/api/v1/assets/`, {
                    params: { search: query, asset_type: type, limit: 10 }
                }).then(res => res.data.assets || []).catch(() => [])
            );
            const assetArrays = await Promise.all(assetPromises);
            const assetCables = assetArrays.flat().map((a: any) => ({
                ...a,
                is_legacy_asset: true
            }));

            // Combine results, prioritizing structured NetworkCables
            setCableResults([...ncCables, ...assetCables]);
            setShowCableDropdown(true);
        } catch (err: any) {
            logger.error('Error searching cables:', err);
            // Fallback to searching assets with separate requests
            try {
                const cableTypes = ['dac_cable', 'ethernet_cable', 'fiber_cable'];
                const assetPromises = cableTypes.map(type =>
                    axios.get(`${API_URL}/api/v1/assets/`, {
                        params: { search: query, asset_type: type, limit: 5 }
                    }).then(res => res.data.assets || []).catch(() => [])
                );
                const assetArrays = await Promise.all(assetPromises);
                setCableResults(assetArrays.flat());
                setShowCableDropdown(true);
            } catch (fallbackErr) {
                logger.error('Fallback cable search failed:', fallbackErr);
            }
        }
    };

    // Select a device
    const selectDevice = (asset: Asset, target: 'A' | 'B') => {
        if (target === 'A') {
            setDeviceA(asset);
            setDeviceASearch(asset.asset_tag);
            setShowDropdownA(false);
            setSelectedPortA(null);
            fetchPorts(asset.id, 'A');
        } else {
            setDeviceB(asset);
            setDeviceBSearch(asset.asset_tag);
            setShowDropdownB(false);
            setSelectedPortB(null);
            fetchPorts(asset.id, 'B');
        }
    };

    // Select a cable
    const selectCable = (asset: Asset) => {
        setSelectedCable(asset);
        setCableSearch(asset.asset_tag);
        setShowCableDropdown(false);
    };

    // Search for cable assemblies
    const searchAssemblies = async (query: string) => {
        try {
            const response = await axios.get(`${API_URL}/api/v1/cable-assemblies/`, {
                params: { status: 'available' }
            });
            const assemblies = response.data || [];
            // Filter by query if provided
            const filtered = query.length > 0
                ? assemblies.filter((a: CableAssembly) =>
                    a.name.toLowerCase().includes(query.toLowerCase()))
                : assemblies;
            setAssemblyResults(filtered);
            setShowAssemblyDropdown(true);
        } catch (err: unknown) {
            logger.error('Error searching assemblies:', err);
            setAssemblyResults([]);
        }
    };

    // Select an assembly
    const selectAssembly = (assembly: CableAssembly) => {
        setSelectedAssembly(assembly);
        setAssemblySearch(assembly.name);
        setShowAssemblyDropdown(false);
    };

    // Create the connection
    const createConnection = async () => {
        // Validate based on mode
        if (useAssemblyMode) {
            if (!selectedAssembly || !selectedPortA || !selectedPortB) {
                setError('Please select a cable assembly and ports on both devices');
                return;
            }
        } else {
            if (!selectedCable || !selectedPortA || !selectedPortB) {
                setError('Please select a cable and ports on both devices');
                return;
            }
        }

        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            if (useAssemblyMode && selectedAssembly) {
                // Deploy cable assembly (installs transceivers + connects cable)
                const response = await axios.post(
                    `${API_URL}/api/v1/cable-assemblies/${selectedAssembly.id}/deploy`,
                    {
                        port_a_id: selectedPortA!.id,
                        port_b_id: selectedPortB!.id
                    }
                );

                setSuccess({
                    message: `Assembly '${selectedAssembly.name}' deployed!`,
                    cable_tag: selectedAssembly.name,
                    device_a: deviceA?.asset_tag || '?',
                    port_a: selectedPortA!.port_number,
                    device_b: deviceB?.asset_tag || '?',
                    port_b: selectedPortB!.port_number
                });
            } else {
                // Original individual cable connection logic
                const responseA = await axios.post(`${API_URL}/api/v1/connections/connect`, {
                    cable_id: selectedCable!.id,
                    port_id: selectedPortA!.id
                });

                if (responseA.data.compatibility) {
                    setCompatibilityResult(responseA.data.compatibility);
                }

                const responseB = await axios.post(`${API_URL}/api/v1/connections/connect`, {
                    cable_id: selectedCable!.id,
                    port_id: selectedPortB!.id
                });

                if (responseB.data.compatibility &&
                    responseB.data.compatibility.level !== 'perfect') {
                    setCompatibilityResult(responseB.data.compatibility);
                }

                setSuccess({
                    message: 'Connection created successfully!',
                    cable_tag: selectedCable!.asset_tag,
                    device_a: deviceA?.asset_tag || '?',
                    port_a: selectedPortA!.port_number,
                    device_b: deviceB?.asset_tag || '?',
                    port_b: selectedPortB!.port_number
                });
            }

            // Reset form after delay
            setTimeout(() => {
                resetForm();
                onConnectionCreated?.();
            }, 5000);

        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message :
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create connection';
            setError(errorMsg);
            logger.error('Error creating connection:', err);
        } finally {
            setLoading(false);
        }
    };

    // Reset the form
    const resetForm = () => {
        setDeviceA(null);
        setDeviceB(null);
        setDeviceASearch('');
        setDeviceBSearch('');
        setPortsA([]);
        setPortsB([]);
        setSelectedPortA(null);
        setSelectedPortB(null);
        setSelectedCable(null);
        setCableSearch('');
        setSelectedAssembly(null);
        setAssemblySearch('');
        setAssemblyResults([]);
        setError(null);
        setSuccess(null);
        setCompatibilityResult(null);
    };

    const getPortTypeIcon = (portType: string): string => {
        const icons: { [key: string]: string } = {
            RJ45: '🔌', SFP: '📡', SFP_PLUS: '📡', SFP28: '📡',
            QSFP: '📶', QSFP28: '📶', QSFP_DD: '📶', QSFP112: '📶',
            OSFP: '⚠️', OSFP_FIN: '🚀', OSFP_FLT: '💻',
            CONSOLE: '💻', OTHER: '🔗',
        };
        return icons[portType] || icons[portType?.toUpperCase()] || '🔌';
    };

    return (
        <div className="p-4 space-y-6">
            <h2 className="text-xl font-bold text-primary">Manual Cable Connection</h2>
            <p className="text-sm text-gray-500">
                Select two devices, choose ports, then pick a cable to connect them.
            </p>

            {/* Error/Success Messages */}
            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                    {error}
                </div>
            )}
            {success && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
                    <div className="flex items-center gap-2 mb-2 font-bold">
                        <span className="text-xl">✅</span>
                        {success.message}
                    </div>
                    <div className="text-sm space-y-1 bg-white/50 p-3 rounded border border-green-100">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">{success.device_a}</span>
                            <span className="text-xs px-1.5 py-0.5 bg-green-100 rounded">Port {success.port_a}</span>
                            <span className="text-green-500">↔</span>
                            <span className="font-semibold">🔗 {success.cable_tag}</span>
                            <span className="text-green-500">↔</span>
                            <span className="font-semibold">{success.device_b}</span>
                            <span className="text-xs px-1.5 py-0.5 bg-green-100 rounded">Port {success.port_b}</span>
                        </div>
                    </div>
                    <div className="mt-3 flex gap-4">
                        <button
                            onClick={() => {
                                setSuccess(null);
                                onConnectionCreated?.();
                            }}
                            className="text-xs font-medium text-green-700 hover:text-green-900 underline underline-offset-4"
                        >
                            View Circuit List
                        </button>
                        <button
                            onClick={() => {
                                resetForm();
                            }}
                            className="text-xs font-medium text-green-700 hover:text-green-900 underline underline-offset-4"
                        >
                            Create Another
                        </button>
                    </div>
                </div>
            )}

            {/* Compatibility Warning */}
            {compatibilityResult && (
                <CompatibilityWarning
                    result={compatibilityResult}
                    onDismiss={() => setCompatibilityResult(null)}
                />
            )}

            {/* Step 1: Select Devices */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Device A */}
                <div className="bg-subtle-card p-4 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Device A
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            value={deviceASearch}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                setDeviceASearch(e.target.value);
                                searchDevices(e.target.value, 'A');
                            }}
                            onFocus={() => {
                                if (searchResultsA.length === 0) {
                                    setSearchResultsA(initialDevices);
                                }
                                setShowDropdownA(true);
                            }}
                            onBlur={() => setTimeout(() => setShowDropdownA(false), 200)}
                            placeholder="Click to select device..."
                            className="input w-full"
                        />
                        {showDropdownA && searchResultsA.length > 0 && (
                            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                <div className="px-3 py-1 text-xs text-gray-400 border-b">Select a device:</div>
                                {searchResultsA.map((asset: Asset) => (
                                    <button
                                        key={asset.id}
                                        onClick={() => selectDevice(asset, 'A')}
                                        className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
                                    >
                                        <span className="font-medium">{asset.asset_tag}</span>
                                        <span className="text-gray-500 ml-2">{asset.manufacturer} {asset.model}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Port selection for Device A */}
                    {deviceA && (
                        <div className="mt-4">
                            <label className="block text-xs text-gray-500 mb-2">Select Port</label>
                            {loadingPortsA ? (
                                <div className="text-sm text-gray-500">Loading ports...</div>
                            ) : portsA.length === 0 ? (
                                <div className="text-sm text-yellow-600">No ports configured</div>
                            ) : (
                                <div className="grid grid-cols-3 gap-2 max-h-32 overflow-y-auto">
                                    {portsA.map((port: NetworkPort) => (
                                        <button
                                            key={port.id}
                                            onClick={() => setSelectedPortA(port)}
                                            className={`p-2 text-xs rounded border transition-colors ${selectedPortA?.id === port.id
                                                ? 'bg-primary border-primary text-white ring-2 ring-primary/20'
                                                : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                                                }`}
                                        >
                                            <span>{getPortTypeIcon(port.port_type)} </span>
                                            {port.port_number}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Device B */}
                <div className="bg-subtle-card p-4 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Device B
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            value={deviceBSearch}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                setDeviceBSearch(e.target.value);
                                searchDevices(e.target.value, 'B');
                            }}
                            onFocus={() => {
                                if (searchResultsB.length === 0) {
                                    setSearchResultsB(initialDevices);
                                }
                                setShowDropdownB(true);
                            }}
                            onBlur={() => setTimeout(() => setShowDropdownB(false), 200)}
                            placeholder="Click to select device..."
                            className="input w-full"
                        />
                        {showDropdownB && searchResultsB.length > 0 && (
                            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                <div className="px-3 py-1 text-xs text-gray-400 border-b">Select a device:</div>
                                {searchResultsB.map((asset: Asset) => (
                                    <button
                                        key={asset.id}
                                        onClick={() => selectDevice(asset, 'B')}
                                        className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
                                    >
                                        <span className="font-medium">{asset.asset_tag}</span>
                                        <span className="text-gray-500 ml-2">{asset.manufacturer} {asset.model}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Port selection for Device B */}
                    {deviceB && (
                        <div className="mt-4">
                            <label className="block text-xs text-gray-500 mb-2">Select Port</label>
                            {loadingPortsB ? (
                                <div className="text-sm text-gray-500">Loading ports...</div>
                            ) : portsB.length === 0 ? (
                                <div className="text-sm text-yellow-600">No ports configured</div>
                            ) : (
                                <div className="grid grid-cols-3 gap-2 max-h-32 overflow-y-auto">
                                    {portsB.map((port: NetworkPort) => (
                                        <button
                                            key={port.id}
                                            onClick={() => setSelectedPortB(port)}
                                            className={`p-2 text-xs rounded border transition-colors ${selectedPortB?.id === port.id
                                                ? 'bg-primary border-primary text-white ring-2 ring-primary/20'
                                                : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                                                }`}
                                        >
                                            <span>{getPortTypeIcon(port.port_type)} </span>
                                            {port.port_number}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Step 2: Select Cable or Assembly */}
            {selectedPortA && selectedPortB && (
                <div className="space-y-4">
                    {/* Mode Toggle */}
                    <div className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Connection Type:</span>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                checked={!useAssemblyMode}
                                onChange={() => setUseAssemblyMode(false)}
                                className="w-4 h-4 text-primary"
                            />
                            <span className="text-sm">Individual Cable</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                checked={useAssemblyMode}
                                onChange={() => setUseAssemblyMode(true)}
                                className="w-4 h-4 text-primary"
                            />
                            <span className="text-sm">📦 Cable Assembly</span>
                        </label>
                    </div>

                    {/* Cable Assembly Selection */}
                    {useAssemblyMode ? (
                        <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Select Cable Assembly
                            </label>
                            <p className="text-xs text-gray-500 mb-2">
                                Pre-configured fiber + transceivers bundle
                            </p>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={assemblySearch}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                        setAssemblySearch(e.target.value);
                                        searchAssemblies(e.target.value);
                                    }}
                                    onFocus={() => {
                                        if (assemblyResults.length === 0) {
                                            searchAssemblies('');
                                        }
                                        setShowAssemblyDropdown(true);
                                    }}
                                    onBlur={() => setTimeout(() => setShowAssemblyDropdown(false), 200)}
                                    placeholder="Click to select assembly..."
                                    className="input w-full"
                                />
                                {showAssemblyDropdown && assemblyResults.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                        <div className="px-3 py-1 text-xs text-gray-400 border-b">Select an assembly:</div>
                                        {assemblyResults.map((assembly: CableAssembly) => (
                                            <button
                                                key={assembly.id}
                                                onClick={() => selectAssembly(assembly)}
                                                className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
                                            >
                                                <span className="font-medium">📦 {assembly.name}</span>
                                                {assembly.description && (
                                                    <span className="text-gray-500 ml-2">{assembly.description}</span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {showAssemblyDropdown && assemblyResults.length === 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm text-gray-500">
                                        No assemblies available. Create one first.
                                    </div>
                                )}
                            </div>
                            {selectedAssembly && (
                                <div className="mt-3 p-2 bg-purple-100 dark:bg-purple-800/30 rounded text-sm">
                                    <span className="font-medium">Selected: {selectedAssembly.name}</span>
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Individual Cable Selection */
                        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Select Cable
                            </label>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={cableSearch}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                        setCableSearch(e.target.value);
                                        searchCables(e.target.value);
                                    }}
                                    onFocus={() => {
                                        if (cableResults.length === 0) {
                                            searchCables('');
                                        }
                                        setShowCableDropdown(true);
                                    }}
                                    onBlur={() => setTimeout(() => setShowCableDropdown(false), 200)}
                                    placeholder="Click to select cable..."
                                    className="input w-full"
                                />
                                {showCableDropdown && cableResults.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                        <div className="px-3 py-1 text-xs text-gray-400 border-b">Select a cable:</div>
                                        {cableResults.map((cable: Asset) => (
                                            <button
                                                key={cable.id}
                                                onClick={() => selectCable(cable)}
                                                className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-sm"
                                            >
                                                <span className="font-medium">🔗 {cable.asset_tag}</span>
                                                <span className="text-gray-500 ml-2">{cable.manufacturer} {cable.model}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Connection Summary */}
            {selectedPortA && selectedPortB && selectedCable && (
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                    <h4 className="font-medium text-green-800 dark:text-green-200 mb-2">Connection Summary</h4>
                    <div className="text-sm text-green-700 dark:text-green-300">
                        <div className="flex items-center gap-2">
                            <span className="font-medium">{deviceA?.asset_tag}</span>
                            <span>Port {selectedPortA.port_number}</span>
                            <span className="text-green-500">→</span>
                            <span className="font-medium">🔗 {selectedCable.asset_tag}</span>
                            <span className="text-green-500">→</span>
                            <span className="font-medium">{deviceB?.asset_tag}</span>
                            <span>Port {selectedPortB.port_number}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
                <button
                    onClick={createConnection}
                    disabled={loading || !selectedCable || !selectedPortA || !selectedPortB}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? 'Connecting...' : 'Create Connection'}
                </button>
                <button
                    onClick={resetForm}
                    className="btn-secondary"
                    disabled={loading}
                >
                    Reset
                </button>
            </div>
        </div>
    );
};

export default ManualCableConnection;
