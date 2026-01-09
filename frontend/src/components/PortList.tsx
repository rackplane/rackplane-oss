// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

export interface NetworkPort {
    id: number;
    asset_id: number;
    port_number: string;
    port_name?: string;
    port_label?: string;
    port_type: string;
    speed_mbps?: number;
    duplex?: string;
    status?: string;
    enabled?: boolean;
    poe_capable?: boolean;
    poe_enabled?: boolean;
    poe_power_watts?: number;
    lane_encoding?: string;
    description?: string;
    notes?: string;
    mac_address?: string;
    connection_id?: number;
    connected_port_id?: number;
    created_at?: string;
    updated_at?: string;
}

interface PortListProps {
    assetId: number;
    onRefresh?: () => void;
    onEdit?: (port: NetworkPort) => void;
    key?: React.Key;
}

const PortList = ({ assetId, onRefresh, onEdit }: PortListProps) => {
    const navigate = useNavigate();
    const [ports, setPorts] = useState<NetworkPort[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [deleting, setDeleting] = useState<number | null>(null);

    useEffect(() => {
        fetchPorts();
    }, [assetId]);

    const fetchPorts = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await axios.get(`${API_URL}/api/v1/network-ports/`, {
                params: { asset_id: assetId }
            });
            setPorts(response.data.ports || []);
        } catch (err: any) {
            logger.error('Error fetching ports:', err);
            setError('Failed to load ports');
            setPorts([]);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (portId: number) => {
        if (!window.confirm('Delete this port?')) return;

        try {
            setDeleting(portId);
            await axios.delete(`${API_URL}/api/v1/network-ports/${portId}`);
            await fetchPorts();
            onRefresh?.();
        } catch (err: any) {
            logger.error('Error deleting port:', err);
            alert('Failed to delete port: ' + (err.response?.data?.detail || err.message));
        } finally {
            setDeleting(null);
        }
    };

    const getPortTypeIcon = (portType: string): string => {
        const icons: { [key: string]: string } = {
            RJ45: '⚡',
            SFP: '🔆',
            SFP_PLUS: '🔆',
            SFP28: '🔆',
            SFP56: '🔆',
            QSFP: '🔆',
            QSFP28: '🔆',
            QSFP56: '🔆',
            QSFP_DD: '🔆',
            QSFP112: '🔆',
            OSFP: '🔆',
            OSFP_FIN: '🔆',
            OSFP_FLT: '🔆',
            FC: '🔆',
            CONSOLE: '💻',
            MGMT: '🔧',
            OTHER: '🔗',
        };
        return icons[portType] || icons[portType.toUpperCase()] || '🔌';
    };

    const getSpeedLabel = (speedMbps?: number): string => {
        if (!speedMbps) return '-';
        if (speedMbps >= 100000) return `${speedMbps / 1000}G`;
        if (speedMbps >= 1000) return `${speedMbps / 1000}G`;
        return `${speedMbps}M`;
    };

    const getStatusBadge = (status?: string, enabled?: boolean) => {
        if (!enabled) {
            return <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">Disabled</span>;
        }
        const statusColors: { [key: string]: string } = {
            active: 'bg-green-100 text-green-800',
            inactive: 'bg-gray-100 text-gray-600',
            up: 'bg-green-100 text-green-800',
            down: 'bg-red-100 text-red-800',
        };
        const colorClass = statusColors[status?.toLowerCase() || ''] || 'bg-gray-100 text-gray-600';
        return <span className={`px-2 py-0.5 text-xs rounded-full ${colorClass}`}>{status || 'Unknown'}</span>;
    };

    if (loading) {
        return (
            <div className="p-4 text-sm text-gray-500 dark:text-gray-400">
                Loading ports...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-sm text-red-500">
                {error}
                <button onClick={fetchPorts} className="ml-2 text-blue-600 hover:underline">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-primary">
                    Network Ports ({ports.length})
                </h3>
                <button
                    onClick={fetchPorts}
                    className="text-sm text-blue-600 hover:text-blue-800"
                    title="Refresh ports"
                >
                    ↻ Refresh
                </button>
            </div>

            {ports.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <p className="text-sm">No ports configured for this device.</p>
                    <p className="text-xs mt-2">Use a port template or add ports manually.</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <th className="px-3 py-2 text-left font-medium text-gray-500">Port</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-500">Type</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-500">Lane</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-500">Speed</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-500">Status</th>
                                <th className="px-3 py-2 text-left font-medium text-gray-500">PoE</th>
                                <th className="px-3 py-2 text-right font-medium text-gray-500">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ports.map((port: NetworkPort) => (
                                <tr
                                    key={port.id}
                                    className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                                >
                                    <td className="px-3 py-2">
                                        <div className="font-medium text-primary">
                                            {port.port_name || port.port_number}
                                        </div>
                                        {port.port_label && (
                                            <div className="text-xs text-gray-500">{port.port_label}</div>
                                        )}
                                    </td>
                                    <td className="px-3 py-2">
                                        <span className="inline-flex items-center gap-1">
                                            <span>{getPortTypeIcon(port.port_type)}</span>
                                            <span className="text-gray-600 dark:text-gray-300">
                                                {port.port_type.toUpperCase().replace('_', '+')}
                                            </span>
                                        </span>
                                    </td>
                                    <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                                        {port.lane_encoding && port.lane_encoding !== 'unknown' ? (
                                            <span className="uppercase font-mono text-xs bg-gray-100 px-1 rounded">
                                                {port.lane_encoding}
                                            </span>
                                        ) : '-'}
                                    </td>
                                    <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                                        {getSpeedLabel(port.speed_mbps)}
                                    </td>
                                    <td className="px-3 py-2">
                                        <div className="flex items-center gap-1">
                                            {getStatusBadge(port.status, port.enabled !== false)}
                                            {/* Status indicator for connected ports - check for physical connection first, then logical status */}
                                            {(port.connection_id || port.connected_port_id || port.status === 'active' || port.status === 'up') && (
                                                <span title={port.connection_id ? "Connected (Physical)" : "Link UP"} className="text-blue-500">🔗</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-3 py-2">
                                        {port.poe_capable ? (
                                            <span className={`text-xs ${port.poe_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                                                {port.poe_enabled ? '⚡ PoE' : 'PoE (off)'}
                                                {port.poe_power_watts && ` ${port.poe_power_watts}W`}
                                            </span>
                                        ) : (
                                            <span className="text-xs text-gray-400">-</span>
                                        )}
                                    </td>
                                    <td className="px-3 py-2 text-right">
                                        <div className="flex justify-end gap-2">
                                            {!port.connection_id && !port.connected_port_id && (
                                                <button
                                                    onClick={() => navigate(`/connections?tab=manual&asset_id=${assetId}&port_id=${port.id}`)}
                                                    className="text-blue-500 hover:text-blue-700 text-xs"
                                                    title="Connect this port"
                                                >
                                                    🔌
                                                </button>
                                            )}
                                            <button
                                                onClick={() => onEdit?.(port)}
                                                className="text-blue-500 hover:text-blue-700 text-xs"
                                                title="Edit port"
                                            >
                                                ✏️
                                            </button>
                                            <button
                                                onClick={() => handleDelete(port.id)}
                                                disabled={deleting === port.id}
                                                className="text-red-500 hover:text-red-700 text-xs disabled:opacity-50"
                                                title="Delete port"
                                            >
                                                {deleting === port.id ? '...' : '🗑️'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default PortList;
