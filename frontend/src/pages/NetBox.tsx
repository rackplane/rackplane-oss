// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface ConnectionStatus {
  connected: boolean;
  message: string;
  configured?: boolean;
  version?: string;
  url?: string;
  error?: string;
}

interface SyncStatus {
  total_assets: number;
  linked_to_netbox: number;
  unlinked: number;
  sync_percentage: number;
}

interface ImportResult {
  success: boolean;
  imported?: number;
  updated?: number;
  total?: number;
  errors?: string[];
  message?: string;
}

const NetBox: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    logger.debug('NetBox page loaded, API_URL:', API_URL);
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [connRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/api/v1/netbox/test-connection`),
        axios.get(`${API_URL}/api/v1/netbox/mapping/status`)
      ]);

      setConnectionStatus(connRes.data);
      setSyncStatus(statusRes.data);
    } catch (error: any) {
      logger.error('Error fetching NetBox data:', error);
      // Set error state so user sees what went wrong
      setConnectionStatus({
        connected: false,
        message: error.response?.data?.detail || error.message || 'Failed to connect to backend API',
        configured: false,
        error: error.message
      });
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/netbox/test-connection`);
      setConnectionStatus(response.data);
    } catch (error: any) {
      logger.error('Error testing connection:', error);
      setConnectionStatus({
        connected: false,
        message: error.response?.data?.detail || 'Failed to test connection',
        configured: false
      });
    } finally {
      setTesting(false);
    }
  };

  const importDevices = async () => {
    setSyncing(true);
    setImportResult(null);
    try {
      const response = await axios.post(`${API_URL}/api/v1/netbox/import/devices`);
      setImportResult(response.data);
      await fetchData(); // Refresh status
    } catch (error: any) {
      logger.error('Error importing devices:', error);
      setImportResult({
        success: false,
        message: error.response?.data?.detail || 'Failed to import devices'
      });
    } finally {
      setSyncing(false);
    }
  };

  const importRacks = async () => {
    setSyncing(true);
    setImportResult(null);
    try {
      const response = await axios.post(`${API_URL}/api/v1/netbox/import/racks`);
      setImportResult(response.data);
      await fetchData(); // Refresh status
    } catch (error: any) {
      logger.error('Error importing racks:', error);
      setImportResult({
        success: false,
        message: error.response?.data?.detail || 'Failed to import racks'
      });
    } finally {
      setSyncing(false);
    }
  };

  const fullSyncFromNetBox = async () => {
    if (!window.confirm('This will import all racks and devices from NetBox. Continue?')) {
      return;
    }

    setSyncing(true);
    setImportResult(null);
    try {
      const response = await axios.post(`${API_URL}/api/v1/netbox/sync/pull`);
      setImportResult(response.data);
      await fetchData(); // Refresh status
    } catch (error: any) {
      logger.error('Error syncing from NetBox:', error);
      setImportResult({
        success: false,
        message: error.response?.data?.detail || 'Failed to sync from NetBox'
      });
    } finally {
      setSyncing(false);
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary">NetBox Integration</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-2">Synchronize datacenter assets with NetBox IPAM/DCIM</p>
      </div>

      {/* Connection Status Card */}
      <div className="card mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-bold text-primary">Connection Status</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Test your NetBox API connection</p>
          </div>
          <button
            onClick={testConnection}
            disabled={testing}
            className="btn-primary"
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>

        {connectionStatus && (
          <div className={`p-4 rounded border ${connectionStatus.connected
              ? 'bg-green-50 dark:bg-green-900 border-green-300 dark:border-green-700'
              : connectionStatus.configured
                ? 'bg-red-50 dark:bg-red-900 border-red-300 dark:border-red-700'
                : 'bg-yellow-50 dark:bg-yellow-900 border-yellow-300 dark:border-yellow-700'
            }`}>
            <div className="flex items-start gap-3">
              <div className={`text-2xl ${connectionStatus.connected ? 'text-green-600' :
                  connectionStatus.configured ? 'text-red-600' : 'text-yellow-600'
                }`}>
                {connectionStatus.connected ? '✓' : connectionStatus.configured ? '✗' : '⚠'}
              </div>
              <div className="flex-1">
                <p className={`font-medium ${connectionStatus.connected ? 'text-green-800 dark:text-green-200' :
                    connectionStatus.configured ? 'text-red-800 dark:text-red-200' : 'text-yellow-800 dark:text-yellow-200'
                  }`}>
                  {connectionStatus.message}
                </p>
                {connectionStatus.version && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Version: {connectionStatus.version}</p>
                )}
                {connectionStatus.url && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">URL: {connectionStatus.url}</p>
                )}
                {connectionStatus.error && (
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">Error: {connectionStatus.error}</p>
                )}
                {!connectionStatus.configured && (
                  <div className="mt-2 text-sm text-primary">
                    <p>Configure NetBox connection in your environment:</p>
                    <code className="block bg-subtle p-2 rounded mt-1 text-primary">
                      NETBOX_URL=https://netbox.example.com<br />
                      NETBOX_TOKEN=your-api-token-here
                    </code>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sync Status */}
      {syncStatus && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="card text-center">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Total Assets</h3>
            <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{syncStatus.total_assets}</p>
          </div>
          <div className="card text-center">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Linked to NetBox</h3>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">{syncStatus.linked_to_netbox}</p>
          </div>
          <div className="card text-center">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Not Linked</h3>
            <p className="text-3xl font-bold text-orange-600 dark:text-orange-400">{syncStatus.unlinked}</p>
          </div>
          <div className="card text-center">
            <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">Sync %</h3>
            <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{syncStatus.sync_percentage}%</p>
          </div>
        </div>
      )}

      {/* Import Results */}
      {importResult && (
        <div className={`card mb-6 ${importResult.success ? 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900' : 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900'
          }`}>
          <h3 className={`text-lg font-bold mb-3 ${importResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'
            }`}>
            {importResult.success ? 'Import Successful' : 'Import Failed'}
          </h3>

          {importResult.success && (
            <div className="grid grid-cols-3 gap-4 mb-3">
              {importResult.imported !== undefined && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Imported</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">{importResult.imported}</p>
                </div>
              )}
              {importResult.updated !== undefined && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Updated</p>
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{importResult.updated}</p>
                </div>
              )}
              {importResult.total !== undefined && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Total</p>
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{importResult.total}</p>
                </div>
              )}
            </div>
          )}

          {importResult.message && (
            <p className="text-sm text-primary mb-2">{importResult.message}</p>
          )}

          {importResult.errors && importResult.errors.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-red-700 dark:text-red-300 mb-1">Errors ({importResult.errors.length}):</p>
              <div className="bg-card p-3 rounded border border-red-200 dark:border-red-700 max-h-40 overflow-y-auto">
                {importResult.errors.map((error, idx) => (
                  <p key={idx} className="text-xs text-red-600 dark:text-red-400 mb-1">{error}</p>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => setImportResult(null)}
            className="mt-3 text-sm text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Sync Actions */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">Sync Operations</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          Import datacenter assets from NetBox into your local inventory
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded hover:border-blue-400 dark:hover:border-blue-500 transition">
            <h3 className="font-bold text-primary mb-2">Import Racks</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Import rack definitions from NetBox. Creates datacenters and racks.
            </p>
            <button
              onClick={importRacks}
              disabled={syncing || !connectionStatus?.connected}
              className="btn-secondary w-full"
            >
              {syncing ? 'Importing...' : 'Import Racks'}
            </button>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded hover:border-blue-400 dark:hover:border-blue-500 transition">
            <h3 className="font-bold text-primary mb-2">Import Devices</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Import device inventory from NetBox. Creates or updates assets.
            </p>
            <button
              onClick={importDevices}
              disabled={syncing || !connectionStatus?.connected}
              className="btn-secondary w-full"
            >
              {syncing ? 'Importing...' : 'Import Devices'}
            </button>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded hover:border-green-400 dark:hover:border-green-500 transition">
            <h3 className="font-bold text-primary mb-2">Full Sync</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Import all racks and devices from NetBox in one operation.
            </p>
            <button
              onClick={fullSyncFromNetBox}
              disabled={syncing || !connectionStatus?.connected}
              className="btn-primary w-full"
            >
              {syncing ? 'Syncing...' : 'Full Sync'}
            </button>
          </div>
        </div>

        {!connectionStatus?.connected && (
          <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900 border border-yellow-300 dark:border-yellow-700 rounded">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Connection to NetBox required. Test connection above and ensure NETBOX_URL and NETBOX_TOKEN are configured.
            </p>
          </div>
        )}
      </div>

      {/* Documentation */}
      <div className="card mt-6">
        <h2 className="text-xl font-bold text-primary mb-4">How It Works</h2>
        <div className="space-y-3 text-sm text-primary">
          <div>
            <h3 className="font-semibold text-primary mb-1">1. Configure Connection</h3>
            <p>Set up your NetBox URL and API token in the environment variables.</p>
          </div>
          <div>
            <h3 className="font-semibold text-primary mb-1">2. Test Connection</h3>
            <p>Verify the connection works and you can access the NetBox API.</p>
          </div>
          <div>
            <h3 className="font-semibold text-primary mb-1">3. Import Data</h3>
            <p>Import racks and devices. The system will automatically create datacenters from NetBox sites.</p>
          </div>
          <div>
            <h3 className="font-semibold text-primary mb-1">4. Automatic Mapping</h3>
            <p>
              Device roles are mapped to asset types (server, switch, router, etc.).
              NetBox IDs are stored for future synchronization.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-primary mb-1">5. Status Tracking</h3>
            <p>
              Assets linked to NetBox are tracked separately. You can see how many assets are synced
              and which ones need attention.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetBox;
