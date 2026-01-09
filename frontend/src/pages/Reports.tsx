// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { formatStatus } from '../utils/formatStatus';

import { useWhiteLabel } from '../contexts/WhiteLabelContext';

interface Datacenter {
  id: number;
  name: string;
  code: string;
}

interface Asset {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  status: string;
  manufacturer: string;
  model: string;
  [key: string]: any;
}

interface AssetUtilizationReport {
  total_assets: number;
  active: number;
  deployed: number;
  maintenance: number;
  failed: number;
  utilization_rate: number;
  by_datacenter: Record<string, any>;
  by_type: Record<string, any>;
}

interface CapacitySummary {
  total_racks: number;
  space: {
    total_u: number;
    used_u: number;
    available_u: number;
    utilization_percent: number;
  };
  power: {
    total_watts: number;
    used_watts: number;
    available_watts: number;
    utilization_percent: number;
  };
  cooling?: {
    total_btu: number;
    used_btu: number;
    available_btu: number;
    utilization_percent: number;
  };
}

interface InventoryValue {
  total_assets_valued: number;
  total_purchase_value: number;
  average_asset_value: number;
  currency: string;
  by_category: Record<string, number>;
  by_datacenter: Record<string, number>;
}

interface LifecycleStatus {
  total_assets: number;
  status_breakdown: Record<string, number>;
  active_count: number;
  maintenance_count: number;
  retired_count: number;
  end_of_life_count: number;
  by_year: Record<string, number>;
}

const Reports: React.FC = () => {
  const { t } = useWhiteLabel();
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [selectedDatacenter, setSelectedDatacenter] = useState<string>('');
  const [activeReport, setActiveReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Report data states
  const [assetUtilization, setAssetUtilization] = useState<AssetUtilizationReport | null>(null);
  const [capacitySummary, setCapacitySummary] = useState<CapacitySummary | null>(null);
  const [inventoryValue, setInventoryValue] = useState<InventoryValue | null>(null);
  const [lifecycleStatus, setLifecycleStatus] = useState<LifecycleStatus | null>(null);
  const [assetsByType, setAssetsByType] = useState<{ [key: string]: Asset[] }>({});
  const [assetsByStatus, setAssetsByStatus] = useState<{ [key: string]: Asset[] }>({});

  useEffect(() => {
    fetchDatacenters();
  }, []);

  const fetchDatacenters = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
    } catch (error) {
      logger.error('Error fetching datacenters:', error);
    }
  };

  const generateAssetUtilizationReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('utilization');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/reports/asset-utilization${params}`);
      setAssetUtilization(response.data);
    } catch (err: any) {
      setError('Failed to generate asset utilization report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateCapacityReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('capacity');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/reports/capacity-summary${params}`);
      setCapacitySummary(response.data);
    } catch (err: any) {
      setError('Failed to generate capacity report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateInventoryValueReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('inventory-value');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/reports/inventory-value${params}`);
      setInventoryValue(response.data);
    } catch (err: any) {
      setError('Failed to generate inventory value report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateLifecycleStatusReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('lifecycle');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/reports/lifecycle-status${params}`);
      setLifecycleStatus(response.data);
    } catch (err: any) {
      setError('Failed to generate lifecycle status report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateAssetsByTypeReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('by-type');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/assets/${params}`);
      const assets = response.data.assets || [];

      // Group by asset type
      const grouped: { [key: string]: Asset[] } = {};
      assets.forEach((asset: Asset) => {
        if (!grouped[asset.asset_type]) {
          grouped[asset.asset_type] = [];
        }
        grouped[asset.asset_type].push(asset);
      });

      setAssetsByType(grouped);
    } catch (err: any) {
      setError('Failed to generate assets by type report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateAssetsByStatusReport = async () => {
    setLoading(true);
    setError(null);
    setActiveReport('by-status');
    try {
      const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
      const response = await axios.get(`${API_URL}/api/v1/assets/${params}`);
      const assets = response.data.assets || [];

      // Group by status
      const grouped: { [key: string]: Asset[] } = {};
      assets.forEach((asset: Asset) => {
        if (!grouped[asset.status]) {
          grouped[asset.status] = [];
        }
        grouped[asset.status].push(asset);
      });

      setAssetsByStatus(grouped);
    } catch (err: any) {
      setError('Failed to generate assets by status report');
      logger.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'xlsx' | 'csv' | 'json') => {
    try {
      if (format === 'json') {
        // Export current data as JSON
        const params = selectedDatacenter ? `?datacenter_id=${selectedDatacenter}` : '';
        const response = await axios.get(`${API_URL}/api/v1/assets/${params}`);
        const dataStr = JSON.stringify(response.data, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `inventory_export_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        URL.revokeObjectURL(url);
      } else {
        // Export via backend endpoint
        const params = selectedDatacenter ? `?format=${format}&datacenter_id=${selectedDatacenter}` : `?format=${format}`;
        const response = await axios.get(`${API_URL}/api/v1/reports/export/inventory${params}`, {
          responseType: 'blob'
        });

        const url = URL.createObjectURL(response.data);
        const link = document.createElement('a');
        link.href = url;
        link.download = `inventory_export_${new Date().toISOString().split('T')[0]}.${format}`;
        link.click();
        URL.revokeObjectURL(url);
      }
    } catch (err: any) {
      alert('Export failed: ' + (err.response?.data?.detail || err.message));
      logger.error(err);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: string } = {
      active: 'badge-success',
      deployed: 'badge-success',
      maintenance: 'badge-warning',
      failed: 'badge-danger',
      decommissioned: 'badge-info',
      received: 'badge-info'
    };
    return `badge ${statusMap[status] || 'badge-info'}`;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">Reports & Analytics</h1>

        {/* Datacenter Filter */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-primary">Filter by {t('location')}:</label>
          <select
            className="input"
            value={selectedDatacenter}
            onChange={(e) => setSelectedDatacenter(e.target.value)}
          >
            <option value="">All {t('locations')}</option>
            {datacenters.map(dc => (
              <option key={dc.id} value={dc.id}>
                {dc.name} ({dc.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Quick Report Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Asset Utilization Report
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View comprehensive asset utilization rates across all {t('locations').toLowerCase()}
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateAssetUtilizationReport}
            disabled={loading}
          >
            {loading && activeReport === 'utilization' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Capacity Summary
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Space, power, and cooling capacity analysis
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateCapacityReport}
            disabled={loading}
          >
            {loading && activeReport === 'capacity' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Inventory Valuation
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Financial reports and asset value analysis
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateInventoryValueReport}
            disabled={loading}
          >
            {loading && activeReport === 'inventory-value' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Lifecycle Status
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Asset status breakdown and lifecycle analysis
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateLifecycleStatusReport}
            disabled={loading}
          >
            {loading && activeReport === 'lifecycle' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Assets by Type
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Group and analyze assets by type
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateAssetsByTypeReport}
            disabled={loading}
          >
            {loading && activeReport === 'by-type' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        <div className="card hover:shadow-xl transition">
          <h3 className="text-lg font-semibold text-primary mb-2">
            Assets by Status
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Group and analyze assets by current status
          </p>
          <button
            className="btn-primary w-full"
            onClick={generateAssetsByStatusReport}
            disabled={loading}
          >
            {loading && activeReport === 'by-status' ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {/* Report Results */}
      {activeReport === 'utilization' && assetUtilization && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Asset Utilization Report</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="text-center p-4 bg-section-card">
              <div className="text-3xl font-bold text-blue-600">{assetUtilization.total_assets}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Total Assets</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">{assetUtilization.active}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Active</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">{assetUtilization.deployed}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Deployed</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-3xl font-bold text-yellow-600">{assetUtilization.maintenance}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Maintenance</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-3xl font-bold text-red-600">{assetUtilization.failed}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Failed</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl font-bold text-purple-600">{assetUtilization.utilization_rate}%</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Utilization</div>
            </div>
          </div>
        </div>
      )}

      {activeReport === 'capacity' && capacitySummary && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Capacity Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold text-primary mb-3">Space Utilization</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Total Racks:</span>
                  <span className="font-semibold">{capacitySummary.total_racks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Total U Space:</span>
                  <span className="font-semibold">{capacitySummary.space.total_u}U</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Used U Space:</span>
                  <span className="font-semibold">{capacitySummary.space.used_u}U</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Available U Space:</span>
                  <span className="font-semibold">{capacitySummary.space.available_u}U</span>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between items-center">
                    <span className="text-primary font-medium">Utilization:</span>
                    <span className="text-xl font-bold text-blue-600">{capacitySummary.space.utilization_percent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${capacitySummary.space.utilization_percent}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-primary mb-3">Power Utilization</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Total Power Capacity:</span>
                  <span className="font-semibold dark:text-gray-200">{capacitySummary.power.total_watts.toLocaleString()}W</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Used Power:</span>
                  <span className="font-semibold dark:text-gray-200">{capacitySummary.power.used_watts.toLocaleString()}W</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Available Power:</span>
                  <span className="font-semibold dark:text-gray-200">{capacitySummary.power.available_watts.toLocaleString()}W</span>
                </div>
                <div className="pt-2 border-t dark:border-gray-700">
                  <div className="flex justify-between items-center">
                    <span className="text-primary font-medium">Utilization:</span>
                    <span className="text-xl font-bold text-green-600 dark:text-green-400">{capacitySummary.power.utilization_percent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${capacitySummary.power.utilization_percent}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeReport === 'inventory-value' && inventoryValue && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Inventory Valuation</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600">{inventoryValue.total_assets_valued}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Assets Valued</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">
                {inventoryValue.currency} {inventoryValue.total_purchase_value.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Total Value</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl font-bold text-purple-600">
                {inventoryValue.currency} {inventoryValue.average_asset_value.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Average Value</div>
            </div>
          </div>
        </div>
      )}

      {activeReport === 'lifecycle' && lifecycleStatus && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Lifecycle Status Report</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            {Object.entries(lifecycleStatus.status_breakdown).map(([status, count]) => (
              <div key={status} className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-primary">{count}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 capitalize">{status}</div>
              </div>
            ))}
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-3xl font-bold text-blue-600">{lifecycleStatus.total_assets}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Total Assets</div>
          </div>
        </div>
      )}

      {activeReport === 'by-type' && Object.keys(assetsByType).length > 0 && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Assets by Type</h2>
          <div className="space-y-4">
            {(Object.entries(assetsByType) as [string, Asset[]][]).map(([type, assets]) => (
              <div key={type} className="border-b border-gray-200 pb-4 last:border-b-0">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-lg font-semibold text-primary capitalize">{type}</h3>
                  <span className="badge badge-info">{assets.length} assets</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Asset Tag</th>
                        <th>Serial Number</th>
                        <th>Manufacturer</th>
                        <th>Model</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assets.slice(0, 10).map(asset => (
                        <tr key={asset.id}>
                          <td className="font-medium">{asset.asset_tag}</td>
                          <td>{asset.serial_number}</td>
                          <td>{asset.manufacturer}</td>
                          <td>{asset.model}</td>
                          <td>
                            <span className={getStatusBadge(asset.status)}>{formatStatus(asset.status)}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {assets.length > 10 && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
                      Showing 10 of {assets.length} assets
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeReport === 'by-status' && Object.keys(assetsByStatus).length > 0 && (
        <div className="card mb-8">
          <h2 className="text-xl font-bold text-primary mb-4">Assets by Status</h2>
          <div className="space-y-4">
            {Object.entries(assetsByStatus).map(([status, assets]) => (
              <div key={status} className="border-b border-gray-200 pb-4 last:border-b-0">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-lg font-semibold text-primary">
                    <span className={getStatusBadge(status)}>{status}</span>
                  </h3>
                  <span className="badge badge-info">{assets.length} assets</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Asset Tag</th>
                        <th>Serial Number</th>
                        <th>Type</th>
                        <th>Manufacturer</th>
                        <th>Model</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assets.slice(0, 10).map(asset => (
                        <tr key={asset.id}>
                          <td className="font-medium">{asset.asset_tag}</td>
                          <td>{asset.serial_number}</td>
                          <td className="capitalize">{asset.asset_type}</td>
                          <td>{asset.manufacturer}</td>
                          <td>{asset.model}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {assets.length > 10 && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
                      Showing 10 of {assets.length} assets
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Options */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">Export Inventory</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Export complete inventory data in various formats
        </p>
        <div className="flex gap-4">
          <button
            className="btn-success"
            onClick={() => handleExport('xlsx')}
          >
            Export as Excel (.xlsx)
          </button>
          <button
            className="btn-success"
            onClick={() => handleExport('csv')}
          >
            Export as CSV
          </button>
          <button
            className="btn-success"
            onClick={() => handleExport('json')}
          >
            Export as JSON
          </button>
        </div>
      </div>
    </div>
  );
};

export default Reports;
