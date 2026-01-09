// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * CableAssemblyManager Component
 * 
 * Create and manage pre-configured fiber cable assemblies:
 * - Bundle 1 fiber cable + 2 optical transceivers
 * - Pre-configure them as a single deployable unit
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface Asset {
    id: number;
    asset_tag: string;
    asset_type: string;
    manufacturer?: string;
    model?: string;
    status?: string;
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

const CableAssemblyManager: React.FC = () => {
    // Assemblies list
    const [assemblies, setAssemblies] = useState<CableAssembly[]>([]);
    const [loading, setLoading] = useState(false);

    // Create form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');

    // Asset selection state
    const [fiberCables, setFiberCables] = useState<Asset[]>([]);
    const [transceivers, setTransceivers] = useState<Asset[]>([]);
    const [selectedFiber, setSelectedFiber] = useState<Asset | null>(null);
    const [selectedTransA, setSelectedTransA] = useState<Asset | null>(null);
    const [selectedTransB, setSelectedTransB] = useState<Asset | null>(null);

    // UI state
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [creating, setCreating] = useState(false);

    // Load assemblies and available assets on mount
    useEffect(() => {
        loadAssemblies();
        loadAvailableAssets();
    }, []);

    const loadAssemblies = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_URL}/api/v1/cable-assemblies/`);
            setAssemblies(response.data || []);
        } catch (err) {
            logger.error('Error loading assemblies:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadAvailableAssets = async () => {
        try {
            // Load fiber cables (any status - user may want to bundle pending items)
            const fiberRes = await axios.get(`${API_URL}/api/v1/assets/`, {
                params: { asset_type: 'fiber_cable', limit: 200 }
            });
            setFiberCables(fiberRes.data?.assets || []);

            // Load transceivers (any status)
            const transRes = await axios.get(`${API_URL}/api/v1/assets/`, {
                params: { asset_type: 'optical_transceiver', limit: 200 }
            });
            setTransceivers(transRes.data?.assets || []);
        } catch (err) {
            logger.error('Error loading available assets:', err);
        }
    };

    const createAssembly = async () => {
        if (!name.trim()) {
            setError('Assembly name is required');
            return;
        }
        if (!selectedFiber || !selectedTransA || !selectedTransB) {
            setError('Please select a fiber cable and two transceivers');
            return;
        }
        if (selectedTransA.id === selectedTransB.id) {
            setError('Transceiver A and B must be different');
            return;
        }

        setCreating(true);
        setError(null);
        setSuccess(null);

        try {
            await axios.post(`${API_URL}/api/v1/cable-assemblies/`, {
                name: name.trim(),
                description: description.trim() || undefined,
                fiber_cable_id: selectedFiber.id,
                transceiver_a_id: selectedTransA.id,
                transceiver_b_id: selectedTransB.id
            });

            setSuccess(`Assembly "${name}" created successfully!`);

            // Reset form
            setName('');
            setDescription('');
            setSelectedFiber(null);
            setSelectedTransA(null);
            setSelectedTransB(null);
            setShowCreateForm(false);

            // Reload lists
            loadAssemblies();
            loadAvailableAssets();

        } catch (err: unknown) {
            const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create assembly';
            setError(errorMsg);
        } finally {
            setCreating(false);
        }
    };

    const deleteAssembly = async (id: number) => {
        if (!window.confirm('Delete this assembly? The components will remain.')) return;

        try {
            await axios.delete(`${API_URL}/api/v1/cable-assemblies/${id}`);
            setSuccess('Assembly deleted');
            loadAssemblies();
        } catch (err) {
            setError('Failed to delete assembly');
        }
    };

    const cloneAssembly = async (assembly: CableAssembly) => {
        setError(null);
        setSuccess(null);

        try {
            const response = await axios.post(`${API_URL}/api/v1/cable-assemblies/${assembly.id}/clone`);
            const newAssembly = response.data;
            setSuccess(`Created "${newAssembly.name}" with Fiber #${newAssembly.fiber_cable_id}, Trans #${newAssembly.transceiver_a_id}, #${newAssembly.transceiver_b_id}`);
            loadAssemblies();
        } catch (err: unknown) {
            const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to clone assembly';
            setError(errorMsg);
        }
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, string> = {
            available: 'bg-green-100 text-green-800',
            deployed: 'bg-blue-100 text-blue-800'
        };
        return styles[status] || 'bg-gray-100 text-gray-800';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-primary">📦 Cable Assemblies</h2>
                    <p className="text-sm text-gray-500">
                        Pre-configured fiber + transceiver bundles
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateForm(!showCreateForm)}
                    className="btn btn-primary"
                >
                    {showCreateForm ? 'Cancel' : '+ New Assembly'}
                </button>
            </div>

            {/* Messages */}
            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                    {error}
                </div>
            )}
            {success && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-800 text-sm">
                    ✅ {success}
                </div>
            )}

            {/* Create Form */}
            {showCreateForm && (
                <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg space-y-4">
                    <h3 className="font-semibold">Create New Assembly</h3>

                    {/* Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Assembly Name *
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., 100G-10M-Assembly-001"
                            className="input w-full"
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description
                        </label>
                        <input
                            type="text"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="e.g., 100G fiber with Intel transceivers"
                            className="input w-full"
                        />
                    </div>

                    {/* Fiber Cable Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Fiber Cable * ({fiberCables.length} available)
                        </label>
                        <select
                            value={selectedFiber?.id || ''}
                            onChange={(e) => {
                                const fiber = fiberCables.find(f => f.id === Number(e.target.value));
                                setSelectedFiber(fiber || null);
                            }}
                            className="input w-full"
                        >
                            <option value="">Select fiber cable...</option>
                            {fiberCables.map(fiber => (
                                <option key={fiber.id} value={fiber.id}>
                                    {fiber.asset_tag} - {fiber.manufacturer} {fiber.model}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Transceiver A Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Transceiver A (End A) * ({transceivers.length} available)
                        </label>
                        <select
                            value={selectedTransA?.id || ''}
                            onChange={(e) => {
                                const trans = transceivers.find(t => t.id === Number(e.target.value));
                                setSelectedTransA(trans || null);
                            }}
                            className="input w-full"
                        >
                            <option value="">Select transceiver...</option>
                            {transceivers.filter(t => t.id !== selectedTransB?.id).map(trans => (
                                <option key={trans.id} value={trans.id}>
                                    {trans.asset_tag} - {trans.manufacturer} {trans.model}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Transceiver B Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Transceiver B (End B) *
                        </label>
                        <select
                            value={selectedTransB?.id || ''}
                            onChange={(e) => {
                                const trans = transceivers.find(t => t.id === Number(e.target.value));
                                setSelectedTransB(trans || null);
                            }}
                            className="input w-full"
                        >
                            <option value="">Select transceiver...</option>
                            {transceivers.filter(t => t.id !== selectedTransA?.id).map(trans => (
                                <option key={trans.id} value={trans.id}>
                                    {trans.asset_tag} - {trans.manufacturer} {trans.model}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Summary */}
                    {selectedFiber && selectedTransA && selectedTransB && (
                        <div className="p-3 bg-white dark:bg-gray-800 rounded border text-sm">
                            <div className="font-medium mb-2">Assembly Preview:</div>
                            <div className="flex items-center gap-2 text-gray-600">
                                <span>📡 {selectedTransA.asset_tag}</span>
                                <span>←</span>
                                <span>🔗 {selectedFiber.asset_tag}</span>
                                <span>→</span>
                                <span>📡 {selectedTransB.asset_tag}</span>
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                        <button
                            onClick={createAssembly}
                            disabled={creating}
                            className="btn btn-primary"
                        >
                            {creating ? 'Creating...' : 'Create Assembly'}
                        </button>
                        <button
                            onClick={() => setShowCreateForm(false)}
                            className="btn btn-secondary"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Assemblies List */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border">
                <div className="p-4 border-b">
                    <h3 className="font-semibold">Existing Assemblies</h3>
                </div>
                {loading ? (
                    <div className="p-4 text-center text-gray-500">Loading...</div>
                ) : assemblies.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <div className="text-4xl mb-2">📦</div>
                        No assemblies yet. Create one to get started!
                    </div>
                ) : (
                    <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-gray-700">
                            <tr>
                                <th className="text-left px-4 py-2 text-sm font-medium">Name</th>
                                <th className="text-left px-4 py-2 text-sm font-medium">Components</th>
                                <th className="text-left px-4 py-2 text-sm font-medium">Status</th>
                                <th className="text-right px-4 py-2 text-sm font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {assemblies.map(assembly => (
                                <tr key={assembly.id} className="border-t hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                    <td className="px-4 py-3">
                                        <div className="font-medium">{assembly.name}</div>
                                        {assembly.description && (
                                            <div className="text-xs text-gray-500">{assembly.description}</div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-600">
                                        <div>🔗 Fiber #{assembly.fiber_cable_id}</div>
                                        <div>📡 Trans A #{assembly.transceiver_a_id}</div>
                                        <div>📡 Trans B #{assembly.transceiver_b_id}</div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusBadge(assembly.status)}`}>
                                            {assembly.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right space-x-3">
                                        <button
                                            onClick={() => cloneAssembly(assembly)}
                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                            title="Clone this assembly with new components"
                                        >
                                            Clone
                                        </button>
                                        {assembly.status === 'available' && (
                                            <button
                                                onClick={() => deleteAssembly(assembly.id)}
                                                className="text-red-600 hover:text-red-800 text-sm"
                                            >
                                                Delete
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default CableAssemblyManager;
