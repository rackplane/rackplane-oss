// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { formatDate, formatCurrency } from '../utils/formatters';

interface ServiceContract {
    id: number;
    name: string;
    contract_type: string;
    vendor: string;
    start_date: string | null;
    end_date: string | null;
    renewal_date: string | null;
    total_cost: number | null;
    cost_period: string;
    currency: string;
    po_number: string | null;
    description: string | null;
    support_level: string | null;
    per_unit_type: string;
    unit_count: number | null;
    status: string;
    notes: string | null;
    days_until_expiry: number | null;
    is_expired: boolean;
    is_expiring_soon: boolean;
    covered_asset_count: number;
}

interface ContractFormData {
    name: string;
    contract_type: string;
    vendor: string;
    start_date: string;
    end_date: string;
    renewal_date: string;
    total_cost: string;
    cost_period: string;
    currency: string;
    po_number: string;
    description: string;
    support_level: string;
    per_unit_type: string;
    unit_count: string;
    status: string;
    notes: string;
}

const ServiceContracts: React.FC = () => {
    const [contracts, setContracts] = useState<ServiceContract[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingContract, setEditingContract] = useState<ServiceContract | null>(null);
    const [formData, setFormData] = useState<ContractFormData>({
        name: '',
        contract_type: 'support',
        vendor: '',
        start_date: '',
        end_date: '',
        renewal_date: '',
        total_cost: '',
        cost_period: 'one_time',
        currency: 'USD',
        po_number: '',
        description: '',
        support_level: '',
        per_unit_type: 'flat_rate',
        unit_count: '',
        status: 'pending',
        notes: '',
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [filterStatus, setFilterStatus] = useState<string>('');

    useEffect(() => {
        fetchContracts();
    }, [filterStatus]);

    const fetchContracts = async () => {
        try {
            let url = `${API_URL}/api/v1/service-contracts`;
            if (filterStatus) {
                url += `?status=${filterStatus}`;
            }
            const response = await axios.get(url);
            setContracts(response.data || []);
        } catch (error) {
            logger.error('Error fetching service contracts:', error);
        } finally {
            setLoading(false);
        }
    };

    const openAddModal = () => {
        setEditingContract(null);
        setFormData({
            name: '',
            contract_type: 'support',
            vendor: '',
            start_date: new Date().toISOString().split('T')[0],
            end_date: '',
            renewal_date: '',
            total_cost: '',
            cost_period: 'one_time',
            currency: 'USD',
            po_number: '',
            description: '',
            support_level: '',
            per_unit_type: 'flat_rate',
            unit_count: '',
            status: 'active',
            notes: '',
        });
        setError(null);
        setShowModal(true);
    };

    const openEditModal = (contract: ServiceContract) => {
        setEditingContract(contract);
        setFormData({
            name: contract.name,
            contract_type: contract.contract_type,
            vendor: contract.vendor,
            start_date: contract.start_date ? contract.start_date.split('T')[0] : '',
            end_date: contract.end_date ? contract.end_date.split('T')[0] : '',
            renewal_date: contract.renewal_date ? contract.renewal_date.split('T')[0] : '',
            total_cost: contract.total_cost?.toString() || '',
            cost_period: contract.cost_period,
            currency: contract.currency,
            po_number: contract.po_number || '',
            description: contract.description || '',
            support_level: contract.support_level || '',
            per_unit_type: contract.per_unit_type,
            unit_count: contract.unit_count?.toString() || '',
            status: contract.status,
            notes: contract.notes || '',
        });
        setError(null);
        setShowModal(true);
    };

    const closeModal = () => {
        setShowModal(false);
        setEditingContract(null);
        setError(null);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);

        try {
            const payload: any = {
                name: formData.name,
                contract_type: formData.contract_type,
                vendor: formData.vendor,
                start_date: formData.start_date || null,
                end_date: formData.end_date || null,
                renewal_date: formData.renewal_date || null,
                total_cost: formData.total_cost ? parseFloat(formData.total_cost) : null,
                cost_period: formData.cost_period,
                currency: formData.currency,
                po_number: formData.po_number || null,
                description: formData.description || null,
                support_level: formData.support_level || null,
                per_unit_type: formData.per_unit_type,
                unit_count: formData.unit_count ? parseInt(formData.unit_count) : null,
                status: formData.status,
                notes: formData.notes || null,
            };

            if (editingContract) {
                await axios.put(`${API_URL}/api/v1/service-contracts/${editingContract.id}`, payload);
            } else {
                await axios.post(`${API_URL}/api/v1/service-contracts`, payload);
            }

            await fetchContracts();
            closeModal();
        } catch (err: any) {
            logger.error('Error saving service contract:', err);
            setError(err.response?.data?.detail || 'Failed to save service contract');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (contract: ServiceContract) => {
        if (!window.confirm(`Delete contract "${contract.name}"?`)) {
            return;
        }
        try {
            await axios.delete(`${API_URL}/api/v1/service-contracts/${contract.id}`);
            await fetchContracts();
        } catch (err: any) {
            logger.error('Error deleting contract:', err);
            alert(err.response?.data?.detail || 'Failed to delete contract');
        }
    };

    const getStatusBadge = (status: string, isExpired: boolean, isExpiringSoon: boolean) => {
        if (isExpired) {
            return 'badge badge-danger';
        }
        if (isExpiringSoon) {
            return 'badge badge-warning';
        }
        const statusMap: { [key: string]: string } = {
            pending: 'badge badge-info',
            active: 'badge badge-success',
            expiring_soon: 'badge badge-warning',
            expired: 'badge badge-danger',
            renewed: 'badge badge-success',
            cancelled: 'badge badge-secondary',
        };
        return statusMap[status] || 'badge badge-info';
    };

    const getTypeBadge = (type: string) => {
        const typeMap: { [key: string]: { class: string; label: string } } = {
            support: { class: 'badge badge-info', label: 'Support' },
            warranty: { class: 'badge badge-success', label: 'Warranty' },
            extended_warranty: { class: 'badge badge-success', label: 'Ext. Warranty' },
            professional_services: { class: 'badge badge-purple', label: 'Prof. Services' },
            maintenance: { class: 'badge badge-warning', label: 'Maintenance' },
            licensing: { class: 'badge badge-info', label: 'Licensing' },
            other: { class: 'badge badge-secondary', label: 'Other' },
        };
        return typeMap[type] || { class: 'badge badge-secondary', label: type };
    };



    // Calculate stats
    const activeCount = contracts.filter((c) => c.status === 'active' && !c.is_expired).length;
    const expiringCount = contracts.filter((c) => c.is_expiring_soon).length;
    const expiredCount = contracts.filter((c) => c.is_expired || c.status === 'expired').length;
    const totalValue = contracts.reduce((sum, c) => sum + (c.total_cost || 0), 0);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-xl text-gray-500 dark:text-gray-400">Loading...</div>
            </div>
        );
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-primary">Service Contracts</h1>
                <button onClick={openAddModal} className="btn-primary">
                    + Add Contract
                </button>
            </div>

            {/* Expiring Soon Alert */}
            {expiringCount > 0 && (
                <div className="card mb-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">⚠️</span>
                        <div>
                            <h3 className="font-bold text-yellow-800 dark:text-yellow-200">
                                {expiringCount} Contract{expiringCount > 1 ? 's' : ''} Expiring Soon
                            </h3>
                            <p className="text-sm text-yellow-700 dark:text-yellow-300">
                                Review and renew these contracts before they expire.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                <div className="card text-center">
                    <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Active</h3>
                    <p className="text-3xl font-bold text-green-600">{activeCount}</p>
                </div>
                <div className="card text-center">
                    <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Expiring Soon</h3>
                    <p className="text-3xl font-bold text-yellow-600">{expiringCount}</p>
                </div>
                <div className="card text-center">
                    <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Expired</h3>
                    <p className="text-3xl font-bold text-red-600">{expiredCount}</p>
                </div>
                <div className="card text-center">
                    <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Total Value</h3>
                    <p className="text-3xl font-bold text-blue-600">{formatCurrency(totalValue, 'USD')}</p>
                </div>
            </div>

            {/* Filters */}
            <div className="card mb-6">
                <div className="flex gap-4 items-center">
                    <label className="text-sm font-medium text-primary">Filter by Status:</label>
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="input"
                    >
                        <option value="">All Contracts</option>
                        <option value="active">Active</option>
                        <option value="pending">Pending</option>
                        <option value="expired">Expired</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                </div>
            </div>

            {/* Contracts Table */}
            <div className="card">
                <h2 className="text-xl font-bold text-primary mb-4">Contracts</h2>
                <div className="overflow-x-auto">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Vendor</th>
                                <th>End Date</th>
                                <th>Cost</th>
                                <th>Status</th>
                                <th>Assets</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {contracts.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-8 text-gray-500 dark:text-gray-400">
                                        No service contracts found
                                    </td>
                                </tr>
                            ) : (
                                contracts.map((contract) => {
                                    const typeInfo = getTypeBadge(contract.contract_type);
                                    return (
                                        <tr key={contract.id}>
                                            <td className="font-medium">
                                                <div>{contract.name}</div>
                                                {contract.po_number && (
                                                    <div className="text-xs text-gray-500">PO: {contract.po_number}</div>
                                                )}
                                            </td>
                                            <td>
                                                <span className={typeInfo.class}>{typeInfo.label}</span>
                                            </td>
                                            <td>{contract.vendor}</td>
                                            <td>
                                                <div>{formatDate(contract.end_date)}</div>
                                                {contract.days_until_expiry !== null && (
                                                    <div
                                                        className={`text-xs ${contract.days_until_expiry < 0
                                                            ? 'text-red-500'
                                                            : contract.days_until_expiry <= 30
                                                                ? 'text-yellow-500'
                                                                : 'text-gray-500'
                                                            }`}
                                                    >
                                                        {contract.days_until_expiry < 0
                                                            ? `Expired ${Math.abs(contract.days_until_expiry)} days ago`
                                                            : `${contract.days_until_expiry} days left`}
                                                    </div>
                                                )}
                                            </td>
                                            <td>{formatCurrency(contract.total_cost, contract.currency)}</td>
                                            <td>
                                                <span
                                                    className={getStatusBadge(
                                                        contract.status,
                                                        contract.is_expired,
                                                        contract.is_expiring_soon
                                                    )}
                                                >
                                                    {contract.is_expired
                                                        ? 'Expired'
                                                        : contract.is_expiring_soon
                                                            ? 'Expiring Soon'
                                                            : contract.status.replace('_', ' ')}
                                                </span>
                                            </td>
                                            <td>
                                                <span className="badge badge-info">{contract.covered_asset_count}</span>
                                            </td>
                                            <td>
                                                <button
                                                    onClick={() => openEditModal(contract)}
                                                    className="text-green-600 hover:text-green-800 mr-3"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(contract)}
                                                    className="text-red-600 hover:text-red-800"
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Add/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-card rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto m-4">
                        <div className="p-6">
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-bold text-primary">
                                    {editingContract ? 'Edit Contract' : 'Add Service Contract'}
                                </h2>
                                <button
                                    onClick={closeModal}
                                    className="text-gray-500 dark:text-gray-400 hover:text-primary text-2xl"
                                >
                                    &times;
                                </button>
                            </div>

                            {error && (
                                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handleSubmit}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Name */}
                                    <div className="md:col-span-2">
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Contract Name <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            name="name"
                                            value={formData.name}
                                            onChange={handleInputChange}
                                            required
                                            className="input w-full"
                                            placeholder="e.g., GPU Node Support - Advanced"
                                        />
                                    </div>

                                    {/* Contract Type */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Type <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            name="contract_type"
                                            value={formData.contract_type}
                                            onChange={handleInputChange}
                                            required
                                            className="input w-full"
                                        >
                                            <option value="support">Support</option>
                                            <option value="warranty">Warranty</option>
                                            <option value="extended_warranty">Extended Warranty</option>
                                            <option value="professional_services">Professional Services</option>
                                            <option value="maintenance">Maintenance</option>
                                            <option value="licensing">Licensing</option>
                                            <option value="other">Other</option>
                                        </select>
                                    </div>

                                    {/* Vendor */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Vendor <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            name="vendor"
                                            value={formData.vendor}
                                            onChange={handleInputChange}
                                            required
                                            className="input w-full"
                                            placeholder="e.g., Penguin Computing"
                                        />
                                    </div>

                                    {/* Status */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Status <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            name="status"
                                            value={formData.status}
                                            onChange={handleInputChange}
                                            required
                                            className="input w-full"
                                        >
                                            <option value="pending">Pending</option>
                                            <option value="active">Active</option>
                                            <option value="expired">Expired</option>
                                            <option value="renewed">Renewed</option>
                                            <option value="cancelled">Cancelled</option>
                                        </select>
                                    </div>

                                    {/* Support Level */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Support Level
                                        </label>
                                        <input
                                            type="text"
                                            name="support_level"
                                            value={formData.support_level}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                            placeholder="e.g., Advanced, 24x7"
                                        />
                                    </div>

                                    {/* Start Date */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Start Date</label>
                                        <input
                                            type="date"
                                            name="start_date"
                                            value={formData.start_date}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                        />
                                    </div>

                                    {/* End Date */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">End Date</label>
                                        <input
                                            type="date"
                                            name="end_date"
                                            value={formData.end_date}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                        />
                                    </div>

                                    {/* Renewal Date */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Renewal Date</label>
                                        <input
                                            type="date"
                                            name="renewal_date"
                                            value={formData.renewal_date}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                        />
                                    </div>

                                    {/* Total Cost */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Total Cost</label>
                                        <input
                                            type="number"
                                            name="total_cost"
                                            value={formData.total_cost}
                                            onChange={handleInputChange}
                                            step="0.01"
                                            className="input w-full"
                                            placeholder="0.00"
                                        />
                                    </div>

                                    {/* Cost Period */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Cost Period</label>
                                        <select
                                            name="cost_period"
                                            value={formData.cost_period}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                        >
                                            <option value="one_time">One Time</option>
                                            <option value="monthly">Monthly</option>
                                            <option value="quarterly">Quarterly</option>
                                            <option value="annual">Annual</option>
                                            <option value="multi_year">Multi-Year</option>
                                        </select>
                                    </div>

                                    {/* Per Unit Type */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Per Unit Type</label>
                                        <select
                                            name="per_unit_type"
                                            value={formData.per_unit_type}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                        >
                                            <option value="flat_rate">Flat Rate</option>
                                            <option value="per_node">Per Node</option>
                                            <option value="per_rack">Per Rack</option>
                                            <option value="per_gpu">Per GPU</option>
                                            <option value="per_device">Per Device</option>
                                            <option value="per_site">Per Site</option>
                                        </select>
                                    </div>

                                    {/* Unit Count */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">Unit Count</label>
                                        <input
                                            type="number"
                                            name="unit_count"
                                            value={formData.unit_count}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                            placeholder="Number of units"
                                        />
                                    </div>

                                    {/* PO Number */}
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">PO Number</label>
                                        <input
                                            type="text"
                                            name="po_number"
                                            value={formData.po_number}
                                            onChange={handleInputChange}
                                            className="input w-full"
                                            placeholder="Purchase order reference"
                                        />
                                    </div>

                                    {/* Description */}
                                    <div className="md:col-span-2">
                                        <label className="block text-sm font-medium text-primary mb-2">Description</label>
                                        <textarea
                                            name="description"
                                            value={formData.description}
                                            onChange={handleInputChange}
                                            rows={3}
                                            className="input w-full"
                                            placeholder="Contract details..."
                                        />
                                    </div>

                                    {/* Notes */}
                                    <div className="md:col-span-2">
                                        <label className="block text-sm font-medium text-primary mb-2">Notes</label>
                                        <textarea
                                            name="notes"
                                            value={formData.notes}
                                            onChange={handleInputChange}
                                            rows={2}
                                            className="input w-full"
                                            placeholder="Internal notes..."
                                        />
                                    </div>
                                </div>

                                {/* Form Actions */}
                                <div className="flex justify-end gap-3 mt-6">
                                    <button type="button" onClick={closeModal} className="btn-secondary" disabled={saving}>
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn-primary" disabled={saving}>
                                        {saving ? 'Saving...' : editingContract ? 'Update Contract' : 'Create Contract'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ServiceContracts;
