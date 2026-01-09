// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import logger from '../utils/logger';

// Helper function to format API errors
const formatError = (error: any): string => {
  if (typeof error === 'string') return error;
  if (Array.isArray(error)) {
    return error.map(err => {
      const field = err.loc ? err.loc.join('.') : 'unknown';
      return `${field}: ${err.msg}`;
    }).join('; ');
  }
  if (typeof error === 'object' && error.msg) return error.msg;
  return 'An error occurred';
};

interface AssetType {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  icon?: string;
  color?: string;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
}

interface AssetTypeFormData {
  name: string;
  display_name: string;
  description: string;
  icon: string;
  color: string;
}

const AssetTypes: React.FC = () => {
  const { isAuthenticated, isTenantAdmin, isSuperAdmin } = useAuth();
  const { t } = useWhiteLabel();
  const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingType, setEditingType] = useState<AssetType | null>(null);
  const [formData, setFormData] = useState<AssetTypeFormData>({
    name: '',
    display_name: '',
    description: '',
    icon: '',
    color: '#3B82F6',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAssetTypes();
  }, []);

  const fetchAssetTypes = async (showLoading: boolean = false) => {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const response = await axios.get(`${API_URL}/api/v1/asset-types/`);
      setAssetTypes(response.data || []);
    } catch (error) {
      logger.error('Error fetching asset types:', error);
    } finally {
      setLoading(false);
    }
  };

  const openAddModal = () => {
    setEditingType(null);
    setFormData({
      name: '',
      display_name: '',
      description: '',
      icon: '',
      color: '#3B82F6',
    });
    setError(null);
    setShowModal(true);
  };

  const openEditModal = (assetType: AssetType) => {
    setEditingType(assetType);
    setFormData({
      name: assetType.name,
      display_name: assetType.display_name,
      description: assetType.description || '',
      icon: assetType.icon || '',
      color: assetType.color || '#3B82F6',
    });
    setError(null);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingType(null);
    setError(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });

    // Auto-generate name from display_name if creating new
    if (name === 'display_name' && !editingType) {
      const generatedName = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
      setFormData(prev => ({
        ...prev,
        name: generatedName,
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        name: formData.name.toLowerCase().replace(/\s+/g, '_'),
        display_name: formData.display_name,
        description: formData.description || null,
        icon: formData.icon || null,
        color: formData.color || null,
      };

      if (editingType) {
        // Update existing asset type (can't change name)
        delete payload.name;
        await axios.put(`${API_URL}/api/v1/asset-types/${editingType.id}`, payload);
      } else {
        // Create new asset type
        await axios.post(`${API_URL}/api/v1/asset-types/`, payload);
      }

      await fetchAssetTypes();
      closeModal();
    } catch (err: any) {
      logger.error('Error saving asset type:', err);
      const errorDetail = err.response?.data?.detail || `Failed to save ${t('item').toLowerCase()} ${t('category').toLowerCase()}`;
      setError(formatError(errorDetail));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (assetType: AssetType) => {
    // Check if assets are using this type
    let assetsUsingType = 0;
    try {
      const assetsResponse = await axios.get(`${API_URL}/api/v1/assets/?asset_type=${assetType.name}&limit=1`);
      assetsUsingType = assetsResponse.data.total || 0;
    } catch (err) {
      // If we can't check, proceed anyway - backend will handle it
    }

    // Build confirmation message
    let confirmMessage = `Are you sure you want to delete "${assetType.display_name}"?`;
    let reassignToId: number | null = null;
    let hardDelete = false;
    let forceDeleteSystem = false;

    if (assetType.is_system) {
      // Stronger warning for system types
      const systemWarning = `⚠️ WARNING: This is a SYSTEM ${t('item').toUpperCase()} ${t('category').toUpperCase()}!\n\n` +
        `System types are default types provided by the system. Deleting them may:\n` +
        `- Break existing functionality\n` +
        `- Cause issues with asset management\n` +
        `- Require manual fixes to restore\n\n` +
        `Are you absolutely sure you want to delete "${assetType.display_name}"?`;
      
      const forceDelete = window.confirm(systemWarning);
      if (!forceDelete) {
        alert('Deletion cancelled. System types should generally not be deleted.');
        return;
      }
      forceDeleteSystem = true;
    }

    if (assetsUsingType > 0) {
      // Ask user to select a target type for reassignment
      const targetTypeName = window.prompt(
        `This ${t('item').toLowerCase()} ${t('category').toLowerCase()} is used by ${assetsUsingType} asset(s).\n\n` +
        `Enter the ID of another ${t('item').toLowerCase()} ${t('category').toLowerCase()} to reassign these assets to, ` +
        `or click Cancel to abort:\n\n` +
        `Available types:\n${assetTypes.filter(t => t.id !== assetType.id && t.is_active).map(t => `  ${t.id}: ${t.display_name}`).join('\n')}`
      );
      
      if (targetTypeName === null) {
        return; // User cancelled
      }
      
      const targetId = parseInt(targetTypeName.trim());
      if (isNaN(targetId)) {
        alert('Invalid ID. Please enter a number.');
        return;
      }
      
      const targetType = assetTypes.find(t => t.id === targetId && t.id !== assetType.id);
      if (!targetType) {
        alert(`Asset type with ID ${targetId} not found or cannot be used.`);
        return;
      }
      
      reassignToId = targetId;
      confirmMessage = `Reassign ${assetsUsingType} asset(s) from "${assetType.display_name}" to "${targetType.display_name}" and delete "${assetType.display_name}"?`;
    }

    if (!window.confirm(confirmMessage)) {
      return;
    }

    // Ask about hard delete
    if (!assetType.is_system) {
      hardDelete = window.confirm(
        `Do you want to permanently delete this ${t('item').toLowerCase()} ${t('category').toLowerCase()} from the database?\n\n` +
        `Yes = Hard delete (permanent)\n` +
        `No = Soft delete (can be reactivated later)`
      );
    }

    try {
      const params = new URLSearchParams();
      if (hardDelete) params.append('hard_delete', 'true');
      if (reassignToId) params.append('reassign_assets_to', reassignToId.toString());
      if (forceDeleteSystem) params.append('force_delete_system', 'true');

      const response = await axios.delete(
        `${API_URL}/api/v1/asset-types/${assetType.id}?${params.toString()}`
      );
      
      if (response.data) {
        const message = response.data.message || 'Deleted successfully';
        const details: string[] = [];
        if (response.data.assets_reassigned > 0) {
          details.push(`${response.data.assets_reassigned} asset(s) reassigned`);
        }
        if (response.data.hard_delete) {
          details.push('Permanently deleted');
        }
        alert(`${message}${details.length > 0 ? '\n' + details.join(', ') : ''}`);
      }
      
      await fetchAssetTypes();
    } catch (err: any) {
      logger.error('Error deleting asset type:', err);
      const errorMsg = err.response?.data?.detail || `Failed to delete ${t('item').toLowerCase()} ${t('category').toLowerCase()}`;
      alert(errorMsg);
    }
  };

  const toggleActive = async (assetType: AssetType) => {
    try {
      await axios.put(`${API_URL}/api/v1/asset-types/${assetType.id}`, {
        is_active: !assetType.is_active
      });
      await fetchAssetTypes();
    } catch (err: any) {
      logger.error('Error toggling asset type:', err);
      alert(`Failed to update ${t('item').toLowerCase()} ${t('category').toLowerCase()}`);
    }
  };

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
        <div>
          <h1 className="text-3xl font-bold text-primary">{t('item')} {t('category')}s</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Manage custom {t('item').toLowerCase()} {t('category').toLowerCase()} definitions</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => fetchAssetTypes(true)} 
            className="btn-secondary"
            title="Refresh asset types list"
            disabled={loading}
          >
            {loading ? 'Refreshing...' : '🔄 Refresh'}
          </button>
          {isAuthenticated && (
            <button onClick={openAddModal} className="btn-primary">
              + Add {t('item')} {t('category')}
            </button>
          )}
          {!isAuthenticated && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">Login to make changes</p>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Total {t('category')}s</h3>
          <p className="text-3xl font-bold text-blue-600">{assetTypes.length}</p>
        </div>
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">System {t('category')}s</h3>
          <p className="text-3xl font-bold text-purple-600">
            {assetTypes.filter(t => t.is_system).length}
          </p>
        </div>
        <div className="card text-center">
          <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Custom {t('category')}s</h3>
          <p className="text-3xl font-bold text-green-600">
            {assetTypes.filter(t => !t.is_system).length}
          </p>
        </div>
      </div>

      {/* Asset Types Table */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">{t('item')} {t('category')} List</h2>
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Display Name</th>
                <th>Name (ID)</th>
                <th>Description</th>
                <th>Color</th>
                <th>Source</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assetTypes.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No {t('item').toLowerCase()} {t('category').toLowerCase()}s found
                  </td>
                </tr>
              ) : (
                assetTypes.map((assetType) => (
                  <tr key={assetType.id}>
                    <td className="font-medium">{assetType.display_name}</td>
                    <td className="text-sm text-gray-500 dark:text-gray-400">{assetType.name}</td>
                    <td className="text-sm">{assetType.description || '-'}</td>
                    <td>
                      {assetType.color && (
                        <div className="flex items-center gap-2">
                          <div
                            className="w-6 h-6 rounded border"
                            style={{ backgroundColor: assetType.color }}
                          ></div>
                          <span className="text-xs text-gray-500 dark:text-gray-400">{assetType.color}</span>
                        </div>
                      )}
                    </td>
                    <td>
                      {assetType.is_system ? (
                        <span className="badge badge-info">System</span>
                      ) : (
                        <span className="badge badge-success">Custom</span>
                      )}
                    </td>
                    <td>
                      {isAuthenticated ? (
                        <button
                          onClick={() => toggleActive(assetType)}
                          className={`badge ${assetType.is_active ? 'badge-success' : 'badge-danger'
                            } cursor-pointer`}
                        >
                          {assetType.is_active ? 'Active' : 'Inactive'}
                        </button>
                      ) : (
                        <span className={`badge ${assetType.is_active ? 'badge-success' : 'badge-danger'
                          }`}>
                          {assetType.is_active ? 'Active' : 'Inactive'}
                        </span>
                      )}
                    </td>
                    <td>
                      {isAuthenticated && (
                        <>
                          <button
                            onClick={() => openEditModal(assetType)}
                            className="text-green-600 hover:text-green-800 mr-3"
                          >
                            Edit
                          </button>
                          {(!assetType.is_system || isTenantAdmin || isSuperAdmin) && (
                            <button
                              onClick={() => handleDelete(assetType)}
                              className="text-red-600 hover:text-red-800"
                              title={assetType.is_system ? "Delete system type (admin only)" : "Delete"}
                            >
                              Delete
                            </button>
                          )}
                        </>
                      )}
                      {!isAuthenticated && (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
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
                  {editingType ? `Edit ${t('item')} ${t('category')}` : `Add New ${t('item')} ${t('category')}`}
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
                  {/* Display Name */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Display Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="display_name"
                      value={formData.display_name}
                      onChange={handleInputChange}
                      required
                      className="input w-full"
                      placeholder="e.g., Network Switch"
                    />
                  </div>

                  {/* Name (ID) */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Name (Identifier) <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      required
                      disabled={!!editingType}
                      className="input w-full"
                      placeholder="e.g., network_switch (auto-generated)"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {editingType
                        ? `Cannot change name of existing ${t('category').toLowerCase()}`
                        : 'Auto-generated from display name (lowercase, underscores)'}
                    </p>
                  </div>

                  {/* Color */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Color
                    </label>
                    <input
                      type="color"
                      name="color"
                      value={formData.color}
                      onChange={handleInputChange}
                      className="input w-full h-10"
                    />
                  </div>

                  {/* Icon */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Icon
                    </label>
                    <input
                      type="text"
                      name="icon"
                      value={formData.icon}
                      onChange={handleInputChange}
                      className="input w-full"
                      placeholder="e.g., server, network, database"
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
                      rows={3}
                      className="input w-full"
                      placeholder={`Brief description of this ${t('item').toLowerCase()} ${t('category').toLowerCase()}...`}
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
                    {saving ? 'Saving...' : editingType ? `Update ${t('category')}` : `Create ${t('category')}`}
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

export default AssetTypes;
