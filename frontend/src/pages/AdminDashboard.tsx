// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useNavigate } from 'react-router-dom';
import logger from '../utils/logger';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import { FeatureGate } from '../components/FeatureGate';
import { UpgradePrompt } from '../components/UpgradePrompt';

interface TenantBreakdown {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  asset_count: number;
  user_count: number;
  subscription_tier: string;
}

interface AdminDashboardStats {
  tenants: {
    total: number;
    active: number;
    inactive: number;
  };
  users: {
    total: number;
    active: number;
    inactive: number;
  };
  assets: {
    total: number;
    active: number;
    deployed: number;
    other: number;
  };
  infrastructure: {
    datacenters: number;
    racks: number;
    storage_containers: number;
  };
  inventory_value: {
    total_purchase_value: number;
  };
  tenant_breakdown: TenantBreakdown[];
  timestamp: string;
}

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useWhiteLabel();
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAdminDashboardStats();
  }, []);

  const fetchAdminDashboardStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/reports/admin/dashboard`);
      setStats(response.data);
    } catch (error) {
      logger.error('Error fetching admin dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-red-600">Failed to load dashboard stats</div>
      </div>
    );
  }

  return (
    <FeatureGate
      feature="admin_portal"
      fallback={
        <div className="p-6">
          <h1 className="text-3xl font-bold text-primary mb-6">Admin Dashboard</h1>
          <UpgradePrompt
            feature="admin_portal"
            showDetails={true}
          />
        </div>
      }
    >
      <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-primary">Admin Dashboard</h1>
          <p className="text-gray-500 mt-2">System-wide overview across all tenants</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Tenants Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Tenants</p>
              <p className="text-3xl font-bold text-primary">{stats.tenants.total}</p>
              <p className="text-xs text-gray-500 mt-1">
                {stats.tenants.active} active, {stats.tenants.inactive} inactive
              </p>
            </div>
            <div className="text-4xl text-blue-500">🏢</div>
          </div>
        </div>

        {/* Users Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Users</p>
              <p className="text-3xl font-bold text-primary">{stats.users.total}</p>
              <p className="text-xs text-gray-500 mt-1">
                {stats.users.active} active, {stats.users.inactive} inactive
              </p>
            </div>
            <div className="text-4xl text-green-500">👥</div>
          </div>
        </div>

        {/* Assets Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Total {t('items')}</p>
              <p className="text-3xl font-bold text-primary">{stats.assets.total}</p>
              <p className="text-xs text-gray-500 mt-1">
                {stats.assets.active} active, {stats.assets.deployed} deployed
              </p>
            </div>
            <div className="text-4xl text-purple-500">📦</div>
          </div>
        </div>

        {/* Inventory Value Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">{t('stock')} Value</p>
              <p className="text-3xl font-bold text-primary">
                {formatCurrency(stats.inventory_value.total_purchase_value)}
              </p>
            </div>
            <div className="text-4xl text-yellow-500">💰</div>
          </div>
        </div>
      </div>

      {/* Infrastructure Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <h3 className="text-lg font-semibold text-primary mb-4">Infrastructure</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-500">{t('locations')}</span>
              <span className="text-xl font-bold text-primary">{stats.infrastructure.datacenters}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">{t('bins')}</span>
              <span className="text-xl font-bold text-primary">{stats.infrastructure.racks}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">{t('containers')}</span>
              <span className="text-xl font-bold text-primary">{stats.infrastructure.storage_containers}</span>
            </div>
          </div>
        </div>

        {/* Asset Status Breakdown */}
        <div className="card">
          <h3 className="text-lg font-semibold text-primary mb-4">{t('item')} Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Active</span>
              <span className="text-xl font-bold text-green-600">{stats.assets.active}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Deployed</span>
              <span className="text-xl font-bold text-blue-600">{stats.assets.deployed}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Other</span>
              <span className="text-xl font-bold text-gray-600">{stats.assets.other}</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-lg font-semibold text-primary mb-4">Quick Actions</h3>
          <div className="space-y-2">
            <button
              onClick={() => navigate('/tenants')}
              className="w-full btn-primary"
            >
              Manage Tenants
            </button>
            <button
              onClick={() => navigate('/users')}
              className="w-full btn-secondary"
            >
              Manage Users
            </button>
            <button
              onClick={() => navigate('/reports')}
              className="w-full btn-secondary"
            >
              View Reports
            </button>
          </div>
        </div>
      </div>

      {/* Tenant Breakdown */}
      {stats.tenant_breakdown && stats.tenant_breakdown.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold text-primary mb-4">Top Tenants by {t('item')} Count</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Tenant</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Status</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-primary">{t('items')}</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-primary">Users</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Tier</th>
                </tr>
              </thead>
              <tbody>
                {stats.tenant_breakdown.map((tenant) => (
                  <tr
                    key={tenant.id}
                    className="border-b border-default hover:bg-table-row-hover transition cursor-pointer"
                    onClick={() => navigate(`/tenants`)}
                  >
                    <td className="py-3 px-4">
                      <div className="font-medium text-primary">{tenant.name}</div>
                      <div className="text-xs text-gray-500">{tenant.slug}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${tenant.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}
                      >
                        {tenant.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-primary">
                      {tenant.asset_count.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-500">
                      {tenant.user_count.toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {tenant.subscription_tier || 'standard'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer with timestamp */}
      <div className="mt-6 text-center text-sm text-gray-500">
        Last updated: {new Date(stats.timestamp).toLocaleString()}
      </div>
    </div>
    </FeatureGate>
  );
};

export default AdminDashboard;

