// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface NetworkPort {
    id: number;
    port_number: string;
    port_name?: string;
    port_type: string;
    speed_mbps?: number;
    lane_encoding?: string;
    enabled?: boolean;
    poe_capable?: boolean;
    poe_max_watts?: number;
    description?: string;
}

interface PortCreateModalProps {
    assetId: number;
    isOpen: boolean;
    onClose: () => void;
    onCreated: () => void;
    editPort?: NetworkPort | null;
    key?: React.Key;
}

const PORT_TYPES = [
    { value: 'RJ45', label: 'RJ45 (Copper)' },
    { value: 'SFP', label: 'SFP (1G)' },
    { value: 'SFP_PLUS', label: 'SFP+ (10G)' },
    { value: 'SFP28', label: 'SFP28 (25G)' },
    { value: 'SFP56', label: 'SFP56 (50G)' },
    { value: 'QSFP', label: 'QSFP (40G)' },
    { value: 'QSFP28', label: 'QSFP28 (100G)' },
    { value: 'QSFP56', label: 'QSFP56 (200G)' },
    { value: 'QSFP_DD', label: 'QSFP-DD (400G)' },
    { value: 'QSFP112', label: 'QSFP112 (400G)' },
    { value: 'OSFP_FIN', label: 'OSFP Finned (800G Switch)' },
    { value: 'OSFP_FLT', label: 'OSFP Flat (800G NIC)' },
    { value: 'OSFP', label: 'OSFP (800G) - Legacy ⚠️' },
    { value: 'CONSOLE', label: 'Console' },
    { value: 'OTHER', label: 'Other' },
];

const SPEED_OPTIONS = [
    { value: 100, label: '100 Mbps' },
    { value: 1000, label: '1 Gbps' },
    { value: 2500, label: '2.5 Gbps' },
    { value: 5000, label: '5 Gbps' },
    { value: 10000, label: '10 Gbps' },
    { value: 25000, label: '25 Gbps' },
    { value: 40000, label: '40 Gbps' },
    { value: 100000, label: '100 Gbps' },
    { value: 400000, label: '400 Gbps' },
    { value: 800000, label: '800 Gbps' },
];

const LANE_ENCODING_OPTIONS = [
    { value: 'unknown', label: 'Unknown' },
    { value: 'nrz', label: 'NRZ (28G/lane)' },
    { value: 'pam4', label: 'PAM4 (56-224G/lane)' },
    { value: 'both', label: 'Both NRZ & PAM4' },
];

const PortCreateModal = ({
    assetId,
    isOpen,
    onClose,
    onCreated,
    editPort
}: PortCreateModalProps) => {
    const [formData, setFormData] = useState({
        port_number: '',
        port_name: '',
        port_type: 'RJ45',
        speed_mbps: 1000,
        lane_encoding: 'unknown',
        enabled: true,
        poe_capable: false,
        poe_max_watts: 15.4,
        description: ''
    });

    React.useEffect(() => {
        if (editPort) {
            setFormData({
                port_number: editPort.port_number,
                port_name: editPort.port_name || '',
                port_type: editPort.port_type,
                speed_mbps: editPort.speed_mbps || 1000,
                lane_encoding: editPort.lane_encoding || 'unknown',
                enabled: editPort.enabled !== false,
                poe_capable: !!editPort.poe_capable,
                poe_max_watts: editPort.poe_max_watts || 15.4,
                description: editPort.description || ''
            });
        } else {
            setFormData({
                port_number: '',
                port_name: '',
                port_type: 'RJ45',
                speed_mbps: 1000,
                lane_encoding: 'unknown',
                enabled: true,
                poe_capable: false,
                poe_max_watts: 15.4,
                description: ''
            });
        }
    }, [editPort, isOpen]);

    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.port_number.trim()) {
            setError('Port number is required');
            return;
        }

        try {
            setSaving(true);
            setError(null);

            if (editPort) {
                await axios.put(`${API_URL}/api/v1/network-ports/${editPort.id}`, {
                    port_number: formData.port_number,
                    port_name: formData.port_name || undefined,
                    port_type: formData.port_type,
                    speed_mbps: formData.speed_mbps,
                    lane_encoding: formData.lane_encoding,
                    enabled: formData.enabled,
                    poe_capable: formData.poe_capable,
                    poe_power_watts: formData.poe_capable ? formData.poe_max_watts : undefined,
                    description: formData.description || undefined
                });
            } else {
                await axios.post(`${API_URL}/api/v1/network-ports/`, {
                    asset_id: assetId,
                    port_number: formData.port_number,
                    port_name: formData.port_name || undefined,
                    port_type: formData.port_type,
                    speed_mbps: formData.speed_mbps,
                    lane_encoding: formData.lane_encoding,
                    enabled: formData.enabled,
                    poe_capable: formData.poe_capable,
                    poe_max_watts: formData.poe_capable ? formData.poe_max_watts : undefined,
                    description: formData.description || undefined
                });
            }

            onCreated();
            onClose();
        } catch (err: any) {
            logger.error('Error creating port:', err);
            setError(err.response?.data?.detail || 'Failed to create port');
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-primary">
                        {editPort ? 'Edit Network Port' : 'Add Network Port'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                        ×
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                Port Number *
                            </label>
                            <input
                                type="text"
                                value={formData.port_number}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, port_number: e.target.value })}
                                className="input w-full"
                                placeholder="e.g., 1, eth0, Gi0/1"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                Port Name
                            </label>
                            <input
                                type="text"
                                value={formData.port_name}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, port_name: e.target.value })}
                                className="input w-full"
                                placeholder="e.g., GigabitEthernet0/1"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                Port Type *
                            </label>
                            <select
                                value={formData.port_type}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, port_type: e.target.value })}
                                className="input w-full"
                            >
                                {PORT_TYPES.map(type => (
                                    <option key={type.value} value={type.value}>{type.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                Speed
                            </label>
                            <select
                                value={formData.speed_mbps}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, speed_mbps: parseInt(e.target.value) })}
                                className="input w-full"
                            >
                                {SPEED_OPTIONS.map(speed => (
                                    <option key={speed.value} value={speed.value}>{speed.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Lane Encoding - shows for high-speed port types */}
                    {['QSFP28', 'QSFP_DD', 'QSFP112', 'OSFP', 'OSFP_FIN', 'OSFP_FLT'].includes(formData.port_type) && (
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                Lane Encoding
                            </label>
                            <select
                                value={formData.lane_encoding}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, lane_encoding: e.target.value })}
                                className="input w-full"
                            >
                                {LANE_ENCODING_OPTIONS.map(enc => (
                                    <option key={enc.value} value={enc.value}>{enc.label}</option>
                                ))}
                            </select>
                            <p className="text-xs text-gray-500 mt-1">
                                NRZ = 28G/lane (100G), PAM4 = 56-224G/lane (400G-800G)
                            </p>
                        </div>
                    )}

                    <div className="flex items-center gap-6">
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={formData.enabled}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, enabled: e.target.checked })}
                                className="rounded"
                            />
                            <span className="text-sm text-gray-600 dark:text-gray-300">Enabled</span>
                        </label>
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={formData.poe_capable}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, poe_capable: e.target.checked })}
                                className="rounded"
                            />
                            <span className="text-sm text-gray-600 dark:text-gray-300">PoE Capable</span>
                        </label>
                    </div>

                    {formData.poe_capable && (
                        <div>
                            <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                                PoE Max Watts
                            </label>
                            <input
                                type="number"
                                value={formData.poe_max_watts}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, poe_max_watts: parseFloat(e.target.value) })}
                                className="input w-full"
                                step="0.1"
                                min="0"
                            />
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
                            Description
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFormData({ ...formData, description: e.target.value })}
                            className="input w-full"
                            rows={2}
                            placeholder="Optional notes about this port"
                        />
                    </div>

                    {error && (
                        <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="btn-secondary"
                            disabled={saving}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={saving}
                        >
                            {saving ? (editPort ? 'Updating...' : 'Creating...') : (editPort ? 'Update Port' : 'Create Port')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default PortCreateModal;
