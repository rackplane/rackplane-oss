// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Port Templates Management Page

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface PortDefinition {
    port_number: string;
    port_type: string;
    speed_mbps: number;
    duplex?: string;
    poe_capable: boolean;
    poe_max_watts?: number;
}

interface PortTemplate {
    id: number;
    manufacturer: string;
    model: string;
    description?: string;
    port_definitions: PortDefinition[];
    created_at?: string;
    updated_at?: string;
}

const PORT_TYPES = [
    { value: 'RJ45', label: 'RJ45 (Copper)' },
    { value: 'SFP', label: 'SFP (1G)' },
    { value: 'SFP_PLUS', label: 'SFP+ (10G)' },
    { value: 'SFP28', label: 'SFP28 (25G)' },
    { value: 'QSFP', label: 'QSFP (40G)' },
    { value: 'QSFP28', label: 'QSFP28 (100G)' },
    { value: 'QSFP_DD', label: 'QSFP-DD (400G)' },
    { value: 'QSFP112', label: 'QSFP112 (400G)' },
    { value: 'OSFP_FIN', label: 'OSFP Finned (800G Switch)' },
    { value: 'OSFP_FLT', label: 'OSFP Flat (800G NIC)' },
    { value: 'OSFP', label: 'OSFP (800G) - Legacy ⚠️' },
    { value: 'FC', label: 'Fiber Channel' },
    { value: 'CONSOLE', label: 'Console' },
    { value: 'MGMT', label: 'Management' },
];

const SPEED_OPTIONS = [
    { value: 100, label: '100 Mbps' },
    { value: 1000, label: '1 Gbps' },
    { value: 2500, label: '2.5 Gbps' },
    { value: 10000, label: '10 Gbps' },
    { value: 25000, label: '25 Gbps' },
    { value: 40000, label: '40 Gbps' },
    { value: 100000, label: '100 Gbps' },
    { value: 400000, label: '400 Gbps' },
    { value: 800000, label: '800 Gbps' },
];

const PortTemplatesPage: React.FC = () => {
    const [templates, setTemplates] = useState<PortTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [editingTemplate, setEditingTemplate] = useState<PortTemplate | null>(null);
    const [showRangeModal, setShowRangeModal] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        manufacturer: '',
        model: '',
        description: '',
        port_definitions: [] as PortDefinition[]
    });

    // Range generator state
    const [rangeData, setRangeData] = useState({
        prefix: 'Gi0/',
        start: 1,
        end: 24,
        port_type: 'RJ45',
        speed_mbps: 1000,
        poe_capable: false
    });

    useEffect(() => {
        fetchTemplates();
    }, []);

    const fetchTemplates = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_URL}/api/v1/port-templates/`);
            setTemplates(response.data || []);
        } catch (err: any) {
            logger.error('Error fetching templates:', err);
            setError('Failed to load templates');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingTemplate(null);
        setFormData({
            manufacturer: '',
            model: '',
            description: '',
            port_definitions: []
        });
        setShowModal(true);
    };

    const handleEdit = (template: PortTemplate) => {
        setEditingTemplate(template);
        setFormData({
            manufacturer: template.manufacturer,
            model: template.model,
            description: template.description || '',
            port_definitions: [...template.port_definitions]
        });
        setShowModal(true);
    };

    const handleDuplicate = (template: PortTemplate) => {
        setEditingTemplate(null);
        setFormData({
            manufacturer: template.manufacturer,
            model: template.model + ' (Copy)',
            description: template.description || '',
            port_definitions: [...template.port_definitions]
        });
        setShowModal(true);
    };

    const handleDelete = async (template: PortTemplate) => {
        if (!window.confirm(`Delete template "${template.manufacturer} ${template.model}"?`)) {
            return;
        }
        try {
            await axios.delete(`${API_URL}/api/v1/port-templates/${template.id}`);
            fetchTemplates();
        } catch (err: any) {
            logger.error('Error deleting template:', err);
            alert('Failed to delete template: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handleSave = async () => {
        if (!formData.manufacturer || !formData.model) {
            alert('Manufacturer and Model are required');
            return;
        }

        try {
            if (editingTemplate) {
                await axios.put(`${API_URL}/api/v1/port-templates/${editingTemplate.id}`, formData);
            } else {
                await axios.post(`${API_URL}/api/v1/port-templates/`, formData);
            }
            setShowModal(false);
            fetchTemplates();
        } catch (err: any) {
            logger.error('Error saving template:', err);
            alert('Failed to save template: ' + (err.response?.data?.detail || err.message));
        }
    };

    const addPort = () => {
        setFormData({
            ...formData,
            port_definitions: [
                ...formData.port_definitions,
                {
                    port_number: `Port${formData.port_definitions.length + 1}`,
                    port_type: 'RJ45',
                    speed_mbps: 1000,
                    duplex: 'full',
                    poe_capable: false
                }
            ]
        });
    };

    const removePort = (index: number) => {
        const newPorts = [...formData.port_definitions];
        newPorts.splice(index, 1);
        setFormData({ ...formData, port_definitions: newPorts });
    };

    const updatePort = (index: number, field: string, value: any) => {
        const newPorts = [...formData.port_definitions];
        (newPorts[index] as any)[field] = value;
        setFormData({ ...formData, port_definitions: newPorts });
    };

    const generateRange = () => {
        const newPorts: PortDefinition[] = [];
        for (let i = rangeData.start; i <= rangeData.end; i++) {
            newPorts.push({
                port_number: `${rangeData.prefix}${i}`,
                port_type: rangeData.port_type,
                speed_mbps: rangeData.speed_mbps,
                duplex: 'full',
                poe_capable: rangeData.poe_capable
            });
        }
        setFormData({
            ...formData,
            port_definitions: [...formData.port_definitions, ...newPorts]
        });
        setShowRangeModal(false);
    };

    const getSpeedLabel = (speedMbps: number): string => {
        const option = SPEED_OPTIONS.find(s => s.value === speedMbps);
        return option ? option.label : `${speedMbps} Mbps`;
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-xl text-gray-500">Loading templates...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800 dark:text-white">Port Templates</h1>
                    <p className="text-gray-500 dark:text-gray-400">
                        Create reusable port configurations for network devices
                    </p>
                </div>
                <button
                    onClick={handleCreate}
                    className="btn-primary flex items-center gap-2"
                >
                    <span>➕</span> Create Template
                </button>
            </div>

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg">
                    {error}
                </div>
            )}

            {/* Templates Grid */}
            {templates.length === 0 ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-8 text-center">
                    <div className="text-5xl mb-4">📋</div>
                    <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        No Port Templates
                    </h3>
                    <p className="text-gray-500 dark:text-gray-400 mb-4">
                        Create your first template to quickly add ports to devices
                    </p>
                    <button onClick={handleCreate} className="btn-primary">
                        Create Your First Template
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {templates.map(template => (
                        <div
                            key={template.id}
                            className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 hover:shadow-lg transition"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <h3 className="font-semibold text-gray-800 dark:text-white">
                                        {template.manufacturer}
                                    </h3>
                                    <p className="text-primary font-medium">{template.model}</p>
                                </div>
                                <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded text-sm">
                                    {template.port_definitions.length} ports
                                </span>
                            </div>

                            {template.description && (
                                <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                                    {template.description}
                                </p>
                            )}

                            {/* Port Preview */}
                            <div className="flex flex-wrap gap-1 mb-3">
                                {template.port_definitions.slice(0, 6).map((def, i) => (
                                    <span
                                        key={i}
                                        className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs"
                                    >
                                        {def.port_type}
                                    </span>
                                ))}
                                {template.port_definitions.length > 6 && (
                                    <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 rounded text-xs">
                                        +{template.port_definitions.length - 6}
                                    </span>
                                )}
                            </div>

                            {/* Actions */}
                            <div className="flex gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                                <button
                                    onClick={() => handleEdit(template)}
                                    className="flex-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition"
                                >
                                    ✏️ Edit
                                </button>
                                <button
                                    onClick={() => handleDuplicate(template)}
                                    className="flex-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition"
                                >
                                    📋 Duplicate
                                </button>
                                <button
                                    onClick={() => handleDelete(template)}
                                    className="px-3 py-1.5 text-sm bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 rounded transition"
                                >
                                    🗑️
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
                        {/* Modal Header */}
                        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
                            <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                                {editingTemplate ? 'Edit Template' : 'Create Port Template'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl"
                            >
                                ×
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-4 overflow-y-auto flex-1 space-y-4">
                            {/* Basic Info */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Manufacturer *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.manufacturer}
                                        onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                                        className="input w-full"
                                        placeholder="e.g., Cisco, Arista, NVIDIA"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Model *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.model}
                                        onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                                        className="input w-full"
                                        placeholder="e.g., Catalyst 2960-24TT-L"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Description
                                </label>
                                <input
                                    type="text"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="input w-full"
                                    placeholder="Optional description"
                                />
                            </div>

                            {/* Port Definitions Section */}
                            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                                <div className="flex justify-between items-center mb-3">
                                    <h3 className="font-semibold text-gray-800 dark:text-white">
                                        Port Definitions ({formData.port_definitions.length})
                                    </h3>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={addPort}
                                            className="px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 rounded transition"
                                        >
                                            ➕ Add Port
                                        </button>
                                        <button
                                            onClick={() => setShowRangeModal(true)}
                                            className="px-3 py-1.5 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 rounded transition"
                                        >
                                            📊 Add Range
                                        </button>
                                    </div>
                                </div>

                                {formData.port_definitions.length === 0 ? (
                                    <div className="text-center py-8 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                        <p className="text-gray-500 dark:text-gray-400 mb-2">No ports defined</p>
                                        <p className="text-sm text-gray-400 dark:text-gray-500">
                                            Use "Add Port" or "Add Range" to define ports
                                        </p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead className="bg-gray-50 dark:bg-gray-700">
                                                <tr>
                                                    <th className="px-3 py-2 text-left">#</th>
                                                    <th className="px-3 py-2 text-left">Port Number</th>
                                                    <th className="px-3 py-2 text-left">Type</th>
                                                    <th className="px-3 py-2 text-left">Speed</th>
                                                    <th className="px-3 py-2 text-center">PoE</th>
                                                    <th className="px-3 py-2 text-center">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {formData.port_definitions.map((port, index) => (
                                                    <tr key={index} className="border-b border-gray-100 dark:border-gray-700">
                                                        <td className="px-3 py-2 text-gray-500">{index + 1}</td>
                                                        <td className="px-3 py-2">
                                                            <input
                                                                type="text"
                                                                value={port.port_number}
                                                                onChange={(e) => updatePort(index, 'port_number', e.target.value)}
                                                                className="input w-24"
                                                            />
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            <select
                                                                value={port.port_type}
                                                                onChange={(e) => updatePort(index, 'port_type', e.target.value)}
                                                                className="input"
                                                            >
                                                                {PORT_TYPES.map(pt => (
                                                                    <option key={pt.value} value={pt.value}>
                                                                        {pt.label}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            <select
                                                                value={port.speed_mbps}
                                                                onChange={(e) => updatePort(index, 'speed_mbps', parseInt(e.target.value))}
                                                                className="input"
                                                            >
                                                                {SPEED_OPTIONS.map(s => (
                                                                    <option key={s.value} value={s.value}>
                                                                        {s.label}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </td>
                                                        <td className="px-3 py-2 text-center">
                                                            <input
                                                                type="checkbox"
                                                                checked={port.poe_capable}
                                                                onChange={(e) => updatePort(index, 'poe_capable', e.target.checked)}
                                                                className="rounded"
                                                            />
                                                        </td>
                                                        <td className="px-3 py-2 text-center">
                                                            <button
                                                                onClick={() => removePort(index)}
                                                                className="text-red-500 hover:text-red-700"
                                                            >
                                                                🗑️
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                className="btn-primary"
                            >
                                {editingTemplate ? 'Save Changes' : 'Create Template'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Range Generator Modal */}
            {showRangeModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md">
                        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                                Add Port Range
                            </h3>
                            <button
                                onClick={() => setShowRangeModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl"
                            >
                                ×
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-3 gap-3">
                                <div className="col-span-3 sm:col-span-1">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Prefix
                                    </label>
                                    <input
                                        type="text"
                                        value={rangeData.prefix}
                                        onChange={(e) => setRangeData({ ...rangeData, prefix: e.target.value })}
                                        className="input w-full"
                                        placeholder="Gi0/"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Start
                                    </label>
                                    <input
                                        type="number"
                                        value={rangeData.start}
                                        onChange={(e) => setRangeData({ ...rangeData, start: parseInt(e.target.value) || 1 })}
                                        className="input w-full"
                                        min="1"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        End
                                    </label>
                                    <input
                                        type="number"
                                        value={rangeData.end}
                                        onChange={(e) => setRangeData({ ...rangeData, end: parseInt(e.target.value) || 1 })}
                                        className="input w-full"
                                        min="1"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Port Type
                                </label>
                                <select
                                    value={rangeData.port_type}
                                    onChange={(e) => setRangeData({ ...rangeData, port_type: e.target.value })}
                                    className="input w-full"
                                >
                                    {PORT_TYPES.map(pt => (
                                        <option key={pt.value} value={pt.value}>{pt.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Speed
                                </label>
                                <select
                                    value={rangeData.speed_mbps}
                                    onChange={(e) => setRangeData({ ...rangeData, speed_mbps: parseInt(e.target.value) })}
                                    className="input w-full"
                                >
                                    {SPEED_OPTIONS.map(s => (
                                        <option key={s.value} value={s.value}>{s.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="range-poe"
                                    checked={rangeData.poe_capable}
                                    onChange={(e) => setRangeData({ ...rangeData, poe_capable: e.target.checked })}
                                    className="rounded"
                                />
                                <label htmlFor="range-poe" className="text-sm text-gray-700 dark:text-gray-300">
                                    PoE Capable
                                </label>
                            </div>

                            {/* Preview */}
                            <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                                    <strong>Preview:</strong> {rangeData.end - rangeData.start + 1} ports
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {rangeData.prefix}{rangeData.start}, {rangeData.prefix}{rangeData.start + 1}, ... {rangeData.prefix}{rangeData.end}
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                            <button
                                onClick={() => setShowRangeModal(false)}
                                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={generateRange}
                                className="btn-primary"
                            >
                                Add {rangeData.end - rangeData.start + 1} Ports
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PortTemplatesPage;
