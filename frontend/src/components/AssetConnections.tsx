// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

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
    port?: string;  // Deprecated compatibility field
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
    port?: string;  // Deprecated compatibility field
    rack_name?: string;
    rack_code?: string;
  } | null;
}

interface AssetConnectionsProps {
  assetId: number;
}

const AssetConnections: React.FC<AssetConnectionsProps> = ({ assetId }) => {
  const [circuits, setCircuits] = useState<Circuit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConnections();
  }, [assetId]);

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/v1/connections/circuits`, {
        params: { device_id: assetId }
      });
      setCircuits(response.data);
    } catch (err: any) {
      logger.error('Error fetching connections:', err);
      setCircuits([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-section-card">
        <p className="text-sm text-gray-500">Loading connections...</p>
      </div>
    );
  }

  if (circuits.length === 0) {
    return (
      <div className="bg-section-card">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Cable Connections</h3>
        <p className="text-xs text-gray-500">No connections found for this device.</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Cable Connections</h3>
      <div className="space-y-3">
        {circuits.map((circuit) => {
          // Determine which end is this device and which is the other end
          const isEndA = circuit.end_a?.device_id === assetId;
          const isEndB = circuit.end_b?.device_id === assetId;
          const otherEnd = isEndA ? circuit.end_b : circuit.end_a;
          const thisEnd = isEndA ? circuit.end_a : circuit.end_b;
          const endLabel = isEndA ? 'A' : 'B';

          if (!thisEnd) return null;

          return (
            <div
              key={circuit.cable.id}
              className="bg-card p-3 rounded border border-default hover:border-blue-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 text-sm">
                    <span className="font-medium text-gray-700">
                      Port {thisEnd.port_number || thisEnd.port_name || thisEnd.port || 'N/A'}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="text-blue-600 font-medium">
                      {circuit.cable.name || circuit.cable.tag}
                    </span>
                    {otherEnd && (
                      <>
                        <span className="text-gray-400">→</span>
                        <Link
                          to={`/assets/${otherEnd.device_id}`}
                          className="text-blue-600 hover:underline font-medium"
                        >
                          {otherEnd.device_name}
                        </Link>
                        <span className="text-xs text-gray-500">
                          (Port {otherEnd.port_number || otherEnd.port_name || otherEnd.port || 'N/A'})
                        </span>
                      </>
                    )}
                  </div>
                  {!otherEnd && (
                    <span className="text-xs text-yellow-600 italic">
                      End {endLabel === 'A' ? 'B' : 'A'} not connected
                    </span>
                  )}
                  <div className="text-xs text-gray-500 mt-1">
                    Cable: {circuit.cable.tag}
                    {circuit.cable.manufacturer && ` • ${circuit.cable.manufacturer}`}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {circuits.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <Link
            to="/connections"
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            View all connections →
          </Link>
        </div>
      )}
    </div>
  );
};

export default AssetConnections;


