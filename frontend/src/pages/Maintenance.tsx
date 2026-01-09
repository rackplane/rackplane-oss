// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { formatDate } from '../utils/formatters';

interface MaintenanceRecord {
  id: number;
  asset_id: number;
  asset?: {
    asset_tag: string;
  };
  title: string;
  maintenance_type: string;
  status: string;
  priority: string;
  scheduled_date: string;
  assigned_to?: string;
  description?: string;
}

interface Prediction {
  id: number;
  asset_id: number;
  asset?: {
    asset_tag: string;
  };
  confidence_score: number;
  failure_type: string;
  failure_severity: string;
  predicted_failure_date: string;
  recommended_action: string;
}

interface Asset {
  id: number;
  asset_tag: string;
}

interface MaintenanceFormData {
  asset_id: string;
  title: string;
  maintenance_type: string;
  priority: string;
  scheduled_date: string;
  assigned_to: string;
  description: string;
}

const Maintenance: React.FC = () => {
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<MaintenanceRecord | null>(null);
  const [formData, setFormData] = useState<MaintenanceFormData>({
    asset_id: '',
    title: '',
    maintenance_type: 'preventive',
    priority: 'medium',
    scheduled_date: '',
    assigned_to: '',
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    fetchAssets();
  }, []);

  const fetchData = async () => {
    try {
      const [maintenanceRes, predictionsRes] = await Promise.all([
        axios.get(`${API_URL}/api/v1/maintenance/`),
        axios.get(`${API_URL}/api/v1/maintenance/predictions/`)
      ]);
      setRecords(maintenanceRes.data.records || []);
      setPredictions(predictionsRes.data || []);
    } catch (error) {
      logger.error('Error fetching maintenance data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssets = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/assets/`);
      setAssets(response.data.assets || []);
    } catch (error) {
      logger.error('Error fetching assets:', error);
    }
  };

  const openAddModal = () => {
    setEditingRecord(null);
    setFormData({
      asset_id: '',
      title: '',
      maintenance_type: 'preventive',
      priority: 'medium',
      scheduled_date: new Date().toISOString().split('T')[0],
      assigned_to: '',
      description: '',
    });
    setError(null);
    setShowModal(true);
  };

  const openEditModal = (record: MaintenanceRecord) => {
    setEditingRecord(record);
    setFormData({
      asset_id: record.asset_id.toString(),
      title: record.title,
      maintenance_type: record.maintenance_type,
      priority: record.priority,
      scheduled_date: record.scheduled_date.split('T')[0],
      assigned_to: record.assigned_to || '',
      description: record.description || '',
    });
    setError(null);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingRecord(null);
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
        asset_id: parseInt(formData.asset_id),
        title: formData.title,
        maintenance_type: formData.maintenance_type,
        priority: formData.priority,
        scheduled_date: new Date(formData.scheduled_date).toISOString(),
        assigned_to: formData.assigned_to || null,
        description: formData.description || null,
      };

      if (editingRecord) {
        await axios.put(`${API_URL}/api/v1/maintenance/${editingRecord.id}`, payload);
      } else {
        await axios.post(`${API_URL}/api/v1/maintenance/`, payload);
      }

      await fetchData();
      closeModal();
    } catch (err: any) {
      logger.error('Error saving maintenance record:', err);
      setError(err.response?.data?.detail || 'Failed to save maintenance record');
    } finally {
      setSaving(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: string } = {
      scheduled: 'badge-info',
      in_progress: 'badge-warning',
      completed: 'badge-success',
      cancelled: 'badge-danger'
    };
    return `badge ${statusMap[status] || 'badge-info'}`;
  };

  const getPriorityBadge = (priority: string) => {
    const priorityMap: { [key: string]: string } = {
      low: 'badge-info',
      medium: 'badge-warning',
      high: 'badge-warning',
      critical: 'badge-danger'
    };
    return `badge ${priorityMap[priority] || 'badge-info'}`;
  };



  // Calculate stats
  const scheduled = records.filter(r => r.status === 'scheduled').length;
  const inProgress = records.filter(r => r.status === 'in_progress').length;
  const completed = records.filter(r => r.status === 'completed').length;

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
        <h1 className="text-3xl font-bold text-primary">Maintenance Management</h1>
        <button onClick={openAddModal} className="btn-primary">+ Schedule Maintenance</button>
      </div>

      {/* Predictive Maintenance Alerts */}
      {predictions.length > 0 && (
        <div className="card mb-6 bg-yellow-50 border border-yellow-200">
          <h2 className="text-xl font-bold text-yellow-800 mb-4">
            Predictive Maintenance Alerts
          </h2>
          <div className="space-y-3">
            {predictions.map((prediction) => (
              <div key={prediction.id} className="bg-card p-4 rounded border-l-4 border-yellow-500">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-primary">
                      {prediction.failure_type.toUpperCase()} Failure Predicted - {prediction.failure_severity}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Asset: {prediction.asset?.asset_tag || `ID ${prediction.asset_id}`} |
                      Confidence: {(prediction.confidence_score * 100).toFixed(0)}% |
                      Predicted Date: {formatDate(prediction.predicted_failure_date)}
                    </p>
                    <p className="text-sm text-primary mt-2">
                      {prediction.recommended_action}
                    </p>
                  </div>
                  <button className="btn-primary text-sm">Schedule</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Maintenance Calendar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Scheduled</h3>
          <p className="text-3xl font-bold text-blue-600">{scheduled}</p>
        </div>
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">In Progress</h3>
          <p className="text-3xl font-bold text-yellow-600">{inProgress}</p>
        </div>
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Completed</h3>
          <p className="text-3xl font-bold text-green-600">{completed}</p>
        </div>
      </div>

      {/* Maintenance Records Table */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">Recent Maintenance Records</h2>
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Asset</th>
                <th>Title</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Scheduled Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No maintenance records found
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr key={record.id}>
                    <td>{record.id}</td>
                    <td className="font-medium">
                      {record.asset?.asset_tag || `Asset ${record.asset_id}`}
                    </td>
                    <td>{record.title}</td>
                    <td className="capitalize">{record.maintenance_type}</td>
                    <td>
                      <span className={getPriorityBadge(record.priority)}>
                        {record.priority}
                      </span>
                    </td>
                    <td>{formatDate(record.scheduled_date)}</td>
                    <td>
                      <span className={getStatusBadge(record.status)}>
                        {record.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => openEditModal(record)}
                        className="text-green-600 hover:text-green-800 mr-3"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-primary">
                  {editingRecord ? 'Edit Maintenance Record' : 'Schedule Maintenance'}
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
                  {/* Asset Selection */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Asset <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="asset_id"
                      value={formData.asset_id}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                    >
                      <option value="">Select an asset...</option>
                      {assets.map(asset => (
                        <option key={asset.id} value={asset.id}>
                          {asset.asset_tag}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Title */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Title <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="title"
                      value={formData.title}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                      placeholder="e.g., Quarterly Server Maintenance"
                    />
                  </div>

                  {/* Maintenance Type */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Type <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="maintenance_type"
                      value={formData.maintenance_type}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                    >
                      <option value="preventive">Preventive</option>
                      <option value="corrective">Corrective</option>
                      <option value="predictive">Predictive</option>
                      <option value="emergency">Emergency</option>
                      <option value="upgrade">Upgrade</option>
                      <option value="replacement">Replacement</option>
                    </select>
                  </div>

                  {/* Priority */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Priority <span className="text-red-500">*</span>
                    </label>
                    <select
                      name="priority"
                      value={formData.priority}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>

                  {/* Scheduled Date */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Scheduled Date <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      name="scheduled_date"
                      value={formData.scheduled_date}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                    />
                  </div>

                  {/* Assigned To */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Assigned To
                    </label>
                    <input
                      type="text"
                      name="assigned_to"
                      value={formData.assigned_to}
                      onChange={handleInputChange}
                      className="input w-full"
                      placeholder="Technician name"
                    />
                  </div>

                  {/* Description */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleInputChange}
                      rows={4}
                      className="input w-full"
                      placeholder="Details about the maintenance work..."
                    />
                  </div>
                </div>

                {/* Form Actions */}
                <div className="flex justify-end gap-3 mt-6">
                  <button
                    type="button"
                    onClick={closeModal}
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
                    {saving ? 'Saving...' : editingRecord ? 'Update Record' : 'Schedule Maintenance'}
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

export default Maintenance;
