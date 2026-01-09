// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import logger from '../utils/logger';
import ManualCableConnection from '../components/ManualCableConnection';
import CableScanner from '../components/CableScanner';

interface Circuit {
  cable: {
    id: number;
    name: string;
    tag: string;
    manufacturer?: string;
    connector_type?: string;  // Phase 2
  };
  end_a: {
    device_id: number;
    device_name: string;
    device_type: string;
    device_model?: string;
    // Phase 2: Port info
    port_id?: number;
    port_number?: string;
    port_name?: string;
    port_type?: string;
    port?: string;  // Deprecated
    rack_name?: string;
    rack_code?: string;
  } | null;
  end_b: {
    device_id: number;
    device_name: string;
    device_type: string;
    device_model?: string;
    // Phase 2: Port info
    port_id?: number;
    port_number?: string;
    port_name?: string;
    port_type?: string;
    port?: string;  // Deprecated
    rack_name?: string;
    rack_code?: string;
  } | null;
}

const ConnectionsList: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [circuits, setCircuits] = useState<Circuit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'manual' | 'scanner'>(
    (searchParams.get('tab') as 'list' | 'manual' | 'scanner') || 'list'
  );

  // Get deep-link params
  const initialAssetId = searchParams.get('asset_id') ? parseInt(searchParams.get('asset_id')!) : undefined;
  const initialPortId = searchParams.get('port_id') ? parseInt(searchParams.get('port_id')!) : undefined;

  useEffect(() => {
    if (isAuthenticated) {
      fetchCircuits();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const tabFromUrl = searchParams.get('tab');
    if (tabFromUrl && (tabFromUrl === 'list' || tabFromUrl === 'manual' || tabFromUrl === 'scanner')) {
      setActiveTab(tabFromUrl as 'list' | 'manual' | 'scanner');
    }
  }, [searchParams]);

  const handleTabChange = (tab: 'list' | 'manual' | 'scanner') => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const fetchCircuits = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/v1/connections/circuits`);
      setCircuits(response.data);
      setError(null);
    } catch (err: any) {
      logger.error('Error fetching circuits:', err);
      setError(err.response?.data?.detail || 'Failed to load circuits');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConnection = async (cableId: number, endLabel: 'A' | 'B') => {
    if (!window.confirm(`Are you sure you want to disconnect ${endLabel === 'A' ? 'End A' : 'End B'} of this cable?`)) {
      return;
    }

    try {
      setDeletingId(cableId);
      // First, get the connection ID for this cable and end
      const cableConnections = await axios.get(`${API_URL}/api/v1/connections/cable/${cableId}`);
      const connection = cableConnections.data.find((c: any) => c.end_label === endLabel);

      if (connection) {
        await axios.delete(`${API_URL}/api/v1/connections/${connection.id}`);
        showToast('Connection removed successfully', 'success');
        fetchCircuits(); // Refresh the list
      }
    } catch (err: any) {
      logger.error('Error deleting connection:', err);
      showToast(err.response?.data?.detail || 'Failed to remove connection', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    if (type === 'error') {
      alert(`Error: ${message}`);
    } else {
      alert(message);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-xl">Loading circuits...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-primary">Connections & Circuits</h1>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        <button
          onClick={() => handleTabChange('list')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'list'
            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
        >
          📋 View Circuits ({circuits.length})
        </button>
        <button
          onClick={() => handleTabChange('manual')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'manual'
            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
        >
          🔗 Manual Connection
        </button>
        <button
          onClick={() => handleTabChange('scanner')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'scanner'
            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
        >
          📷 Cable Scanner
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Manual Connection Tab */}
      {activeTab === 'manual' && (
        <div className="bg-card rounded-lg shadow p-6">
          <ManualCableConnection
            initialAssetId={initialAssetId}
            initialPortId={initialPortId}
            onConnectionCreated={() => {
              fetchCircuits();
              handleTabChange('list');
            }}
          />
        </div>
      )}

      {/* Cable Scanner Tab */}
      {activeTab === 'scanner' && (
        <div className="bg-card rounded-lg shadow overflow-hidden">
          <CableScanner />
        </div>
      )}

      {/* Circuit List Tab */}
      {activeTab === 'list' && (
        <>
          {circuits.length === 0 ? (
            <div className="bg-card rounded-lg shadow p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400 mb-4">No circuits found.</p>
              <button
                onClick={() => setActiveTab('manual')}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline"
              >
                Create your first connection
              </button>
            </div>
          ) : (
            <div className="bg-card shadow rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-table-header">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        End A (Source)
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Connection Media
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        End B (Destination)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-gray-200 dark:divide-gray-700">
                    {circuits.map((circuit) => (
                      <tr key={circuit.cable.id} className="hover:bg-table-row-hover">
                        {/* END A */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          {circuit.end_a ? (
                            <div className="flex flex-col">
                              <Link
                                to={`/assets/${circuit.end_a.device_id}`}
                                className="font-bold text-blue-600 hover:underline"
                              >
                                {circuit.end_a.device_name}
                              </Link>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {circuit.end_a.rack_name}
                                {circuit.end_a.rack_code && ` (${circuit.end_a.rack_code})`}
                              </span>
                              <span className="text-xs text-gray-400 dark:text-gray-500 dark:text-gray-400">
                                {circuit.end_a.device_type} • Port: {circuit.end_a.port_number || circuit.end_a.port_name || circuit.end_a.port || 'N/A'}
                              </span>
                            </div>
                          ) : (
                            <span className="text-red-400 italic text-sm">Disconnected</span>
                          )}
                        </td>

                        {/* The CABLE (Middle) */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-subtle-card text-primary">
                            <span className="mx-2">━━━━</span>
                            <span className="font-semibold">{circuit.cable.name || circuit.cable.tag}</span>
                            <span className="mx-2">━━━━</span>
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {circuit.cable.manufacturer && `${circuit.cable.manufacturer} • `}
                            ID: {circuit.cable.tag}
                          </div>
                        </td>

                        {/* END B */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          {circuit.end_b ? (
                            <div className="flex flex-col">
                              <Link
                                to={`/assets/${circuit.end_b.device_id}`}
                                className="font-bold text-blue-600 hover:underline"
                              >
                                {circuit.end_b.device_name}
                              </Link>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {circuit.end_b.rack_name}
                                {circuit.end_b.rack_code && ` (${circuit.end_b.rack_code})`}
                              </span>
                              <span className="text-xs text-gray-400 dark:text-gray-500 dark:text-gray-400">
                                {circuit.end_b.device_type} • Port: {circuit.end_b.port_number || circuit.end_b.port_name || circuit.end_b.port || 'N/A'}
                              </span>
                            </div>
                          ) : (
                            <span className="text-yellow-500 italic text-sm">Waiting for connection...</span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex justify-end space-x-2">
                            {circuit.end_a && (
                              <button
                                onClick={() => handleDeleteConnection(circuit.cable.id, 'A')}
                                disabled={deletingId === circuit.cable.id}
                                className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:text-gray-400 dark:disabled:text-gray-500 dark:text-gray-400"
                                title="Disconnect End A"
                              >
                                Unplug A
                              </button>
                            )}
                            {circuit.end_b && (
                              <button
                                onClick={() => handleDeleteConnection(circuit.cable.id, 'B')}
                                disabled={deletingId === circuit.cable.id}
                                className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:text-gray-400 dark:disabled:text-gray-500 dark:text-gray-400"
                                title="Disconnect End B"
                              >
                                Unplug B
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ConnectionsList;
