// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface NetworkPort {
    id: number;
    port_number: string;
    port_name?: string;
    port_label?: string;
    port_type: string;
    speed_mbps?: number;
    status?: string;
    enabled?: boolean;
    poe_capable?: boolean;
}

interface PortSelectorModalProps {
    isOpen: boolean;
    deviceId: number;
    deviceName: string;
    onSelect: (portId: number, portLabel: string) => void;
    onCancel: () => void;
}

const PortSelectorModal: React.FC<PortSelectorModalProps> = ({
    isOpen,
    deviceId,
    deviceName,
    onSelect,
    onCancel
}) => {
    const [ports, setPorts] = useState<NetworkPort[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedPortId, setSelectedPortId] = useState<number | null>(null);

    useEffect(() => {
        if (isOpen && deviceId) {
            fetchPorts();
        }
    }, [isOpen, deviceId]);

    const fetchPorts = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await axios.get(`${API_URL}/api/v1/network-ports/`, {
                params: { asset_id: deviceId }
            });
            setPorts(response.data.ports || []);
            setSelectedPortId(null);
        } catch (err: any) {
            logger.error('Error fetching ports:', err);
            setError('Failed to load ports');
        } finally {
            setLoading(false);
        }
    };

    const handleConfirm = () => {
        if (!selectedPortId) return;

        const selectedPort = ports.find(p => p.id === selectedPortId);
        if (selectedPort) {
            onSelect(selectedPortId, selectedPort.port_label || selectedPort.port_number);
        }
    };

    const getPortTypeIcon = (portType: string): string => {
        const icons: { [key: string]: string } = {
            RJ45: '🔌',
            SFP: '📡',
            SFP_PLUS: '📡',
            SFP28: '📡',
            QSFP: '📶',
            QSFP28: '📶',
            QSFP_DD: '📶',
            QSFP112: '📶',
            OSFP: '🚀',
            CONSOLE: '💻',
            OTHER: '🔗',
        };
        return icons[portType] || icons[portType.toUpperCase()] || '🔌';
    };

    const getSpeedLabel = (speedMbps?: number): string => {
        if (!speedMbps) return '';
        if (speedMbps >= 1000) return `${speedMbps / 1000}G`;
        return `${speedMbps}M`;
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div>
                        <h2 className="text-lg font-semibold text-primary">Select Port</h2>
                        <p className="text-sm text-gray-500">Device: {deviceName}</p>
                    </div>
                    <button
                        onClick={onCancel}
                        className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                        ×
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="text-center py-8 text-gray-500">Loading ports...</div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-500">{error}</div>
                    ) : ports.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            <p>No ports configured on this device.</p>
                            <p className="text-sm mt-2">Add ports in the device detail page first.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                            {ports.map((port) => (
                                <button
                                    key={port.id}
                                    onClick={() => setSelectedPortId(port.id)}
                                    className={`
                    p-3 rounded-lg border-2 text-left transition-all
                    ${selectedPortId === port.id
                                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                            : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                                        }
                    ${!port.enabled ? 'opacity-50' : ''}
                  `}
                                    disabled={!port.enabled}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-lg">{getPortTypeIcon(port.port_type)}</span>
                                        <span className="font-medium text-primary">
                                            {port.port_number}
                                        </span>
                                    </div>
                                    {port.port_name && (
                                        <div className="text-xs text-gray-500 truncate">
                                            {port.port_name}
                                        </div>
                                    )}
                                    <div className="text-xs text-gray-400 mt-1">
                                        {port.port_type.toUpperCase().replace('_', '+')}
                                        {port.speed_mbps && ` • ${getSpeedLabel(port.speed_mbps)}`}
                                    </div>
                                    {!port.enabled && (
                                        <div className="text-xs text-yellow-600 mt-1">Disabled</div>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                    <button
                        onClick={onCancel}
                        className="btn-secondary"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!selectedPortId}
                        className="btn-primary disabled:opacity-50"
                    >
                        Connect to Port
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PortSelectorModal;
