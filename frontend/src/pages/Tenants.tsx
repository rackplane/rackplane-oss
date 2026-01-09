// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { FeatureGate } from '../components/FeatureGate';
import { UpgradePrompt } from '../components/UpgradePrompt';

interface Tenant {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  subscription_tier: string;
  contact_email?: string;
  contact_phone?: string;
  created_at: string;
  updated_at: string;
  user_count?: number;
}

interface User {
  id: number;
  username: string;
  is_active: boolean;
  tenant_id?: number;
}

const Tenants: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showUsersModal, setShowUsersModal] = useState(false);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [showEditUserModal, setShowEditUserModal] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [tenantUsers, setTenantUsers] = useState<User[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);

  // User form states
  const [newUserUsername, setNewUserUsername] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [editUserUsername, setEditUserUsername] = useState('');
  const [editUserIsActive, setEditUserIsActive] = useState(true);
  const [resetPassword, setResetPassword] = useState('');

  // Form states
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [newTier, setNewTier] = useState('starter');
  const [newEmail, setNewEmail] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [editName, setEditName] = useState('');
  const [editSlug, setEditSlug] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [editTier, setEditTier] = useState('starter');
  const [editEmail, setEditEmail] = useState('');
  const [editPhone, setEditPhone] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      setError('You must be logged in to manage tenants');
      setLoading(false);
      return;
    }
    fetchTenants();
    fetchAllUsers();
  }, [isAuthenticated]);

  const fetchTenants = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/v1/tenants/`);
      setTenants(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch tenants');
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/users/`);
      setAllUsers(response.data);
    } catch (err: any) {
      logger.error('Failed to fetch users:', err);
    }
  };

  const fetchTenantUsers = async (tenantId: number) => {
    try {
      setError(''); // Clear previous errors
      const response = await axios.get(`${API_URL}/api/v1/tenants/${tenantId}/users`);
      logger.debug('Tenant users response:', response.data);
      setTenantUsers(response.data || []);
    } catch (err: any) {
      logger.error('Failed to fetch tenant users:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch tenant users';
      setError(errorMsg);
      setTenantUsers([]); // Clear users on error
    }
  };

  const handleAddTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/v1/tenants/`, {
        name: newName,
        slug: newSlug,
        subscription_tier: newTier,
        contact_email: newEmail || null,
        contact_phone: newPhone || null,
      });
      setShowAddModal(false);
      resetAddForm();
      fetchTenants();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create tenant');
    }
  };

  const handleEditTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenant) return;
    try {
      await axios.put(`${API_URL}/api/v1/tenants/${selectedTenant.id}`, {
        name: editName,
        slug: editSlug,
        is_active: editIsActive,
        subscription_tier: editTier,
        contact_email: editEmail || null,
        contact_phone: editPhone || null,
      });
      setShowEditModal(false);
      setSelectedTenant(null);
      fetchTenants();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update tenant');
    }
  };

  const handleBackupTenant = async (tenant: Tenant) => {
    try {
      setError(''); // Clear previous errors

      // Call the backup export endpoint
      // Note: For super admins, this exports all tenants, but we can filter client-side
      // For now, we'll export and let the user know it includes all tenants if they're super admin
      const response = await axios.get(`${API_URL}/api/v1/backup/export`, {
        responseType: 'json'
      });

      // Filter to only this tenant's data if the backup includes multiple tenants
      let backupData = response.data;
      if (backupData.metadata?.scope === 'full_system') {
        // Filter to only this tenant's data
        const filteredData: any = {
          metadata: {
            ...backupData.metadata,
            scope: 'tenant',
            tenant_id: tenant.id,
            tenant_name: tenant.name,
            filtered_from_full_backup: true
          },
          tables: {}
        };

        // Filter each table to only include this tenant's data
        if (backupData.tables) {
          for (const [tableName, tableData] of Object.entries(backupData.tables)) {
            if (tableData && typeof tableData === 'object' && 'data' in tableData) {
              const table = tableData as any;
              const filteredRecords = table.data.filter((record: any) => {
                // For tenants table, match by id
                if (tableName === 'tenants') {
                  return record.id === tenant.id;
                }
                // For all other tables, match by tenant_id
                return record.tenant_id === tenant.id;
              });

              filteredData.tables[tableName] = {
                ...table,
                data: filteredRecords,
                count: filteredRecords.length
              };
            }
          }
        }

        backupData = filteredData;
      }

      // Convert to JSON string
      const jsonString = JSON.stringify(backupData, null, 2);

      // Create a blob and download it
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `tenant_backup_${tenant.slug}_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      alert(`Tenant backup downloaded: ${tenant.name}`);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to backup tenant';
      logger.error('Error backing up tenant:', err);
      setError(errorMessage);
      alert(`Failed to backup tenant: ${errorMessage}`);
    }
  };

  const handleDeleteTenant = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this tenant? This action cannot be undone.')) {
      return;
    }
    try {
      setError(''); // Clear previous errors
      await axios.delete(`${API_URL}/api/v1/tenants/${id}`, {
        validateStatus: (status) => status === 204 || status < 500 // Accept 204 as success
      });
      // 204 No Content means success
      fetchTenants();
      // Show success message
      alert('Tenant deleted successfully');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete tenant';
      logger.error('Error deleting tenant:', err);
      logger.error('Error response:', err.response);
      setError(errorMessage);
      // Also show alert so user sees the error
      alert(`Failed to delete tenant: ${errorMessage}`);
    }
  };

  const handleAssignUser = async (userId: number) => {
    if (!selectedTenant) return;
    try {
      await axios.post(`${API_URL}/api/v1/tenants/${selectedTenant.id}/users/${userId}`);
      fetchTenantUsers(selectedTenant.id);
      fetchAllUsers();
      fetchTenants();
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to assign user to tenant');
    }
  };

  const handleRemoveUser = async (userId: number) => {
    if (!selectedTenant) return;
    if (!window.confirm('Remove this user from the tenant? They will be reassigned to the default tenant.')) {
      return;
    }
    try {
      await axios.delete(`${API_URL}/api/v1/tenants/${selectedTenant.id}/users/${userId}`);
      fetchTenantUsers(selectedTenant.id);
      fetchAllUsers();
      fetchTenants();
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove user from tenant');
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenant) return;
    try {
      await axios.post(`${API_URL}/api/v1/tenants/${selectedTenant.id}/users`, {
        username: newUserUsername,
        password: newUserPassword,
        tenant_id: selectedTenant.id,
      });
      setShowAddUserModal(false);
      setNewUserUsername('');
      setNewUserPassword('');
      fetchTenantUsers(selectedTenant.id);
      fetchAllUsers();
      fetchTenants();
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      await axios.put(`${API_URL}/api/v1/users/${selectedUser.id}`, {
        is_active: editUserIsActive,
      });
      setShowEditUserModal(false);
      setSelectedUser(null);
      if (selectedTenant) {
        fetchTenantUsers(selectedTenant.id);
      }
      fetchAllUsers();
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      await axios.post(`${API_URL}/api/v1/users/${selectedUser.id}/reset-password`, {
        new_password: resetPassword,
      });
      setShowResetPasswordModal(false);
      setSelectedUser(null);
      setResetPassword('');
      setError('');
      alert('Password reset successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return;
    }
    try {
      await axios.delete(`${API_URL}/api/v1/users/${userId}`);
      if (selectedTenant) {
        fetchTenantUsers(selectedTenant.id);
      }
      fetchAllUsers();
      fetchTenants();
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    }
  };

  const openEditUserModal = (user: User) => {
    setSelectedUser(user);
    setEditUserUsername(user.username);
    setEditUserIsActive(user.is_active);
    setShowEditUserModal(true);
  };

  const openResetPasswordModal = (user: User) => {
    setSelectedUser(user);
    setResetPassword('');
    setShowResetPasswordModal(true);
  };

  const openEditModal = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setEditName(tenant.name);
    setEditSlug(tenant.slug);
    setEditIsActive(tenant.is_active);
    setEditTier(tenant.subscription_tier);
    setEditEmail(tenant.contact_email || '');
    setEditPhone(tenant.contact_phone || '');
    setShowEditModal(true);
  };

  const openUsersModal = async (tenant: Tenant) => {
    setSelectedTenant(tenant);
    await fetchTenantUsers(tenant.id);
    setShowUsersModal(true);
  };

  const resetAddForm = () => {
    setNewName('');
    setNewSlug('');
    setNewTier('starter');
    setNewEmail('');
    setNewPhone('');
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  };

  const handleNameChange = (value: string) => {
    setNewName(value);
    if (!newSlug || newSlug === generateSlug(newName)) {
      setNewSlug(generateSlug(value));
    }
  };

  const availableUsers = allUsers.filter(
    user => !tenantUsers.some(tu => tu.id === user.id)
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl">Loading tenants...</div>
      </div>
    );
  }

  return (
    <FeatureGate
      feature="multi_tenant"
      fallback={
        <div className="p-6">
          <h1 className="text-3xl font-bold text-primary mb-6">Tenant Management</h1>
          <UpgradePrompt
            feature="multi_tenant"
            showDetails={true}
          />
        </div>
      }
    >
      <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-primary">Tenant Management</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          + Add Tenant
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-card rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-table-header">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Company Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Slug
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Tier
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Users
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-card divide-y divide-gray-200">
            {tenants.map((tenant) => (
              <tr key={tenant.id} className={!tenant.is_active ? 'opacity-50' : ''}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-primary">{tenant.name}</div>
                  {tenant.contact_email && (
                    <div className="text-sm text-gray-500 dark:text-gray-400">{tenant.contact_email}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-primary">{tenant.slug}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {tenant.subscription_tier}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {tenant.user_count || 0}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${tenant.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                      }`}
                  >
                    {tenant.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  <button
                    onClick={() => openUsersModal(tenant)}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Users
                  </button>
                  <button
                    onClick={() => openEditModal(tenant)}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleBackupTenant(tenant)}
                    className="text-green-600 hover:text-green-900"
                    title="Download tenant backup as JSON"
                  >
                    Backup
                  </button>
                  {tenant.slug !== 'default' && (
                    <button
                      onClick={() => handleDeleteTenant(tenant.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Tenant Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Add New Tenant</h2>
            <form onSubmit={handleAddTenant}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary">Company Name</label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Slug</label>
                  <input
                    type="text"
                    value={newSlug}
                    onChange={(e) => setNewSlug(e.target.value)}
                    pattern="^[a-z0-9-]+$"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">URL-friendly identifier (lowercase, hyphens only)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Subscription Tier</label>
                  <select
                    value={newTier}
                    onChange={(e) => setNewTier(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="community">Community (1 user)</option>
                    <option value="starter">Starter (1 user)</option>
                    <option value="pro">Pro (unlimited users)</option>
                    <option value="msp">MSP (unlimited users)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Contact Email (Optional)</label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Contact Phone (Optional)</label>
                  <input
                    type="tel"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    resetAddForm();
                  }}
                  className="px-4 py-2 border border-default rounded-md text-primary hover:bg-table-row-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Create Tenant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Tenant Modal */}
      {showEditModal && selectedTenant && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Edit Tenant</h2>
            <form onSubmit={handleEditTenant}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary">Company Name</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Slug</label>
                  <input
                    type="text"
                    value={editSlug}
                    onChange={(e) => setEditSlug(e.target.value)}
                    pattern="^[a-z0-9-]+$"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Status</label>
                  <select
                    value={editIsActive ? 'true' : 'false'}
                    onChange={(e) => setEditIsActive(e.target.value === 'true')}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Subscription Tier</label>
                  <select
                    value={editTier}
                    onChange={(e) => setEditTier(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="community">Community (1 user)</option>
                    <option value="starter">Starter (1 user)</option>
                    <option value="pro">Pro (unlimited users)</option>
                    <option value="msp">MSP (unlimited users)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Contact Email (Optional)</label>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Contact Phone (Optional)</label>
                  <input
                    type="tel"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedTenant(null);
                  }}
                  className="px-4 py-2 border border-default rounded-md text-primary hover:bg-table-row-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Update Tenant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Users Modal */}
      {showUsersModal && selectedTenant && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">
                User Management - {selectedTenant.name}
              </h2>
              <button
                onClick={() => {
                  setShowUsersModal(false);
                  setSelectedTenant(null);
                  setTenantUsers([]);
                }}
                className="text-gray-500 dark:text-gray-400 hover:text-primary"
              >
                ✕
              </button>
            </div>

            <div className="mb-4 flex justify-end">
              <button
                onClick={() => setShowAddUserModal(true)}
                className="px-4 py-2 text-white rounded transition"
                style={{ backgroundColor: 'var(--success)' }}
              >
                + Add New User
              </button>
            </div>

            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">Current Users ({tenantUsers.length})</h3>
              {tenantUsers.length > 0 ? (
                <div className="bg-card border rounded-lg overflow-hidden" style={{ borderColor: 'var(--border-color)' }}>
                  <table className="min-w-full divide-y" style={{ borderColor: 'var(--border-color)' }}>
                    <thead className="bg-table-header">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Username</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-card divide-y" style={{ borderColor: 'var(--border-color)' }}>
                      {tenantUsers.map((user) => (
                        <tr key={user.id}>
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-primary">
                            {user.username}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className="px-2 py-1 text-xs font-semibold rounded-full"
                              style={user.is_active
                                ? { backgroundColor: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)' }
                                : { backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)' }
                              }
                            >
                              {user.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium space-x-2">
                            <button
                              onClick={() => openEditUserModal(user)}
                              style={{ color: 'var(--primary)' }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => openResetPasswordModal(user)}
                              style={{ color: 'var(--warning)' }}
                            >
                              Reset Password
                            </button>
                            {tenantUsers.length > 1 ? (
                              <button
                                onClick={() => handleRemoveUser(user.id)}
                                style={{ color: '#f97316' }}
                              >
                                Remove
                              </button>
                            ) : null}
                            <button
                              onClick={() => handleDeleteUser(user.id)}
                              style={{ color: 'var(--danger)' }}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-sm">No users assigned to this tenant</p>
              )}
            </div>

            {availableUsers.length > 0 && (
              <div className="mb-4">
                <h3 className="text-lg font-semibold mb-2">Assign Existing Users</h3>
                <div className="border rounded-lg p-4 max-h-48 overflow-y-auto" style={{ backgroundColor: 'rgba(0, 123, 255, 0.1)', borderColor: 'rgba(0, 123, 255, 0.3)' }}>
                  <div className="space-y-2">
                    {availableUsers.map((user) => (
                      <div
                        key={user.id}
                        className="flex justify-between items-center p-2 bg-card rounded"
                      >
                        <span className="text-sm text-primary">{user.username}</span>
                        <button
                          onClick={() => handleAssignUser(user.id)}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                        >
                          Assign
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => {
                  setShowUsersModal(false);
                  setSelectedTenant(null);
                  setTenantUsers([]);
                }}
                className="px-4 py-2 text-white rounded-md"
                style={{ backgroundColor: 'var(--secondary)' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && selectedTenant && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Add New User to {selectedTenant.name}</h2>
            <form onSubmit={handleAddUser}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary">Username</label>
                  <input
                    type="text"
                    value={newUserUsername}
                    onChange={(e) => setNewUserUsername(e.target.value)}
                    className="mt-1 block w-full rounded-md shadow-sm input"
                    required
                    minLength={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Password</label>
                  <input
                    type="password"
                    value={newUserPassword}
                    onChange={(e) => setNewUserPassword(e.target.value)}
                    className="mt-1 block w-full rounded-md shadow-sm input"
                    required
                    minLength={6}
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Minimum 6 characters</p>
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddUserModal(false);
                    setNewUserUsername('');
                    setNewUserPassword('');
                  }}
                  className="px-4 py-2 border border-default rounded-md text-primary hover:bg-table-row-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-white rounded-md"
                  style={{ backgroundColor: 'var(--success)' }}
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditUserModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Edit User: {selectedUser.username}</h2>
            <form onSubmit={handleUpdateUser}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary">Username</label>
                  <input
                    type="text"
                    value={editUserUsername}
                    disabled
                    className="mt-1 block w-full rounded-md shadow-sm input"
                    style={{ backgroundColor: 'var(--bg-light)' }}
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Username cannot be changed</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary">Status</label>
                  <select
                    value={editUserIsActive ? 'true' : 'false'}
                    onChange={(e) => setEditUserIsActive(e.target.value === 'true')}
                    className="mt-1 block w-full rounded-md shadow-sm"
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditUserModal(false);
                    setSelectedUser(null);
                  }}
                  className="px-4 py-2 border border-default rounded-md text-primary hover:bg-table-row-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-white rounded-md"
                  style={{ backgroundColor: 'var(--primary)' }}
                >
                  Update User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPasswordModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Reset Password for {selectedUser.username}</h2>
            <form onSubmit={handleResetPassword}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary">New Password</label>
                  <input
                    type="password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                    minLength={6}
                  />
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Minimum 6 characters</p>
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowResetPasswordModal(false);
                    setSelectedUser(null);
                    setResetPassword('');
                  }}
                  className="px-4 py-2 border border-default rounded-md text-primary hover:bg-table-row-hover"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
                >
                  Reset Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
    </FeatureGate>
  );
};

export default Tenants;

