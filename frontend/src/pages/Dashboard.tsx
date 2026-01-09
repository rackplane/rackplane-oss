// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import { FeatureGate } from '../components/FeatureGate';
import StorageBoxList from '../components/StorageBoxList';
import logger from '../utils/logger';
import { formatAssetType } from '../utils/formatAssetType';

interface AssetCountByType {
  asset_type: string;
  display_name: string;
  count: number;
}

interface LowStockItem {
  container_id: number;
  container_name: string;
  current_count: number;
  min_threshold: number;
  low_stock_types?: Array<{
    asset_type: string;
    manufacturer: string;
    model: string;
    count: number;
  }>;
}

interface UpcomingMaintenance {
  id: number;
  asset_id: number;
  asset_tag?: string;
  title: string;
  description?: string;
  maintenance_type: string;
  status: string;
  priority: string;
  scheduled_date: string;
  estimated_duration_hours?: number;
}

interface DashboardStats {
  asset_utilization: {
    total_assets: number;
    active: number;
    deployed: number;
    maintenance: number;
    failed: number;
  };
  capacity: {
    total_racks: number;
    space: {
      utilization_percent: number;
    };
    power: {
      utilization_percent: number;
    };
  };
  inventory_value: {
    total_purchase_value: number;
  };
  asset_counts_by_type?: AssetCountByType[];
  low_stock_items?: LowStockItem[];
  upcoming_maintenance?: UpcomingMaintenance[];
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { isSuperAdmin } = useAuth();
  const { t, refreshConfig } = useWhiteLabel();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDevTroubleshooting, setShowDevTroubleshooting] = useState(false);  // Default: OFF

  useEffect(() => {
    fetchDashboardStats();
    // Refresh white-label config to ensure terminology is up-to-date (e.g. if switching tenants/verticals)
    refreshConfig();

    // Load tenant settings from API (tenant-wide)
    const fetchTenantSettings = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/v1/tenants/current/settings`);
        setShowDevTroubleshooting(response.data.show_dev_troubleshooting || false);
      } catch (err: unknown) {
        logger.error('Failed to load tenant settings:', err);
        // Default to OFF on error
        setShowDevTroubleshooting(false);
      }
    };

    fetchTenantSettings();

    // Listen for settings changes
    const handleSettingsChange = (event: CustomEvent) => {
      if (event.detail?.showDevTroubleshooting !== undefined) {
        setShowDevTroubleshooting(event.detail.showDevTroubleshooting);
      }
    };

    window.addEventListener('settingsChanged', handleSettingsChange as EventListener);
    return () => {
      window.removeEventListener('settingsChanged', handleSettingsChange as EventListener);
    };
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/reports/dashboard/summary`);
      setStats(response.data);
    } catch (err: unknown) {
      logger.error('Error fetching dashboard stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-primary mb-8">
        {t('location')} {t('stock')} Dashboard
      </h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <h3 className="text-gray-500 text-sm font-medium mb-2">Total {t('items')}</h3>
          <p className="text-3xl font-bold text-blue-600">
            {stats?.asset_utilization.total_assets || 0}
          </p>
        </div>

        <div className="card">
          <h3 className="text-gray-500 text-sm font-medium mb-2">Active {t('items')}</h3>
          <p className="text-3xl font-bold text-green-600">
            {stats?.asset_utilization.active || 0}
          </p>
        </div>

        <div className="card">
          <h3 className="text-gray-500 text-sm font-medium mb-2">In Maintenance</h3>
          <p className="text-3xl font-bold text-yellow-600">
            {stats?.asset_utilization.maintenance || 0}
          </p>
        </div>

        <div className="card">
          <h3 className="text-gray-500 text-sm font-medium mb-2">Failed</h3>
          <p className="text-3xl font-bold text-red-600">
            {stats?.asset_utilization.failed || 0}
          </p>
        </div>
      </div>

      {/* Capacity Overview */}
      <FeatureGate feature="rack_viz">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">Space Utilization</h2>
            <div className="relative pt-1">
              <div className="flex mb-2 items-center justify-between">
                <div>
                  <span className="text-xs font-semibold inline-block text-blue-600">
                    {stats?.capacity.space.utilization_percent.toFixed(1) || 0}%
                  </span>
                </div>
              </div>
              <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
                <div
                  style={{ width: `${stats?.capacity.space.utilization_percent || 0}%` }}
                  className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-600"
                ></div>
              </div>
            </div>
            <p className="text-sm text-gray-500">
              Total {t('bins')}: {stats?.capacity.total_racks || 0}
            </p>
          </div>

          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">Power Utilization</h2>
            <div className="relative pt-1">
              <div className="flex mb-2 items-center justify-between">
                <div>
                  <span className="text-xs font-semibold inline-block text-green-600">
                    {stats?.capacity.power.utilization_percent.toFixed(1) || 0}%
                  </span>
                </div>
              </div>
              <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-green-200">
                <div
                  style={{ width: `${stats?.capacity.power.utilization_percent || 0}%` }}
                  className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-green-600"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </FeatureGate>

      {/* Inventory Value */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">{t('stock')} Value</h2>
        <p className="text-4xl font-bold text-primary">
          ${stats?.inventory_value.total_purchase_value.toLocaleString() || 0}
        </p>
        <p className="text-sm text-gray-500 mt-2">Total {t('item').toLowerCase()} value</p>
      </div>

      <div className="mt-8 card">
        <h2 className="text-xl font-bold text-primary mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button onClick={() => navigate('/assets?modal=create')} className="btn-primary">Add {t('item')}</button>

          <FeatureGate feature="maintenance">
            <button onClick={() => navigate('/maintenance')} className="btn-primary">Schedule Maintenance</button>
          </FeatureGate>

          <FeatureGate feature="reports">
            <button onClick={() => navigate('/reports')} className="btn-primary">View Reports</button>
          </FeatureGate>

          <button onClick={() => navigate('/stock')} className="btn-primary">Audit {t('stock')}</button>
        </div>
      </div>

      {/* Asset Counts by Type */}
      {stats?.asset_counts_by_type && stats.asset_counts_by_type.length > 0 && (
        <div className="mt-8 card">
          <h2 className="text-xl font-bold text-primary mb-4">{t('items')} by {t('category')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.asset_counts_by_type.map((item) => (
              <div key={item.asset_type} className="bg-muted p-4 rounded-lg border border-border">
                <div className="text-sm text-gray-500 mb-1">{item.display_name}</div>
                <div className="text-2xl font-bold text-primary">{item.count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Low Stock Items */}
      {stats?.low_stock_items && stats.low_stock_items.length > 0 && (
        <div className="mt-8 card border-l-4 border-yellow-500">
          <h2 className="text-xl font-bold text-primary mb-4 flex items-center">
            <span className="text-yellow-600 dark:text-yellow-500 mr-2">⚠️</span>
            Low Stock Alerts
          </h2>
          <div className="space-y-3">
            {stats.low_stock_items.map((item) => (
              <div key={item.container_id} className="bg-yellow-50 dark:bg-yellow-900/30 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-primary">{item.container_name}</div>
                    <div className="text-sm text-gray-500 mt-1">
                      Current: {item.current_count} / Minimum: {item.min_threshold}
                    </div>
                    {item.low_stock_types && item.low_stock_types.length > 0 && (
                      <div className="text-xs text-gray-500 mt-2">
                        Low stock types: {item.low_stock_types.map(stockType => {
                          const name = (stockType.manufacturer || stockType.model)
                            ? `${stockType.manufacturer || ''} ${stockType.model || ''}`.trim()
                            : formatAssetType(stockType.asset_type);
                          return `${name} (${stockType.count})`;
                        }).join(', ')}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => navigate(`/storage-containers/${item.container_id}`)}
                    className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white rounded text-sm transition"
                  >
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Maintenance */}
      {stats?.upcoming_maintenance && stats.upcoming_maintenance.length > 0 && (
        <div className="mt-8 card">
          <h2 className="text-xl font-bold text-primary mb-4">Upcoming Maintenance</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Scheduled Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {stats.upcoming_maintenance.map((maintenance) => (
                  <tr key={maintenance.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap">
                      {maintenance.asset_tag ? (
                        <button
                          onClick={() => navigate(`/assets/${maintenance.asset_id}`)}
                          className="text-primary hover:text-primary/80 underline"
                        >
                          {maintenance.asset_tag}
                        </button>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-foreground">{maintenance.title}</div>
                      {maintenance.description && (
                        <div className="text-xs text-gray-500">{maintenance.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {maintenance.maintenance_type}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${maintenance.priority === 'high' ? 'badge-danger' :
                        maintenance.priority === 'medium' ? 'badge-warning' :
                          'badge-success ' // Using success for low priority as neutral
                        }`}>
                        {maintenance.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {new Date(maintenance.scheduled_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${maintenance.status === 'in_progress' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                        'bg-muted text-gray-500'
                        }`}>
                        {maintenance.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Storage Boxes & Low Stock Alerts */}
      <div className="mt-8 card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-primary">{t('containers')} & {t('stock')} Levels</h2>
        </div>
        <StorageBoxList />
      </div>

      {/* Troubleshooting Actions */}
      <div className="mt-8 card">
        <h2 className="text-xl font-bold text-primary mb-4">Troubleshooting</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {showDevTroubleshooting && (
            <button
              onClick={() => navigate('/dev-troubleshooting')}
              className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg font-semibold transition"
            >
              DEV Troubleshooting
            </button>
          )}
          {isSuperAdmin && (
            <button
              onClick={() => navigate('/diagnostic')}
              className="bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-3 rounded-lg font-semibold transition"
            >
              Diagnostic
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
