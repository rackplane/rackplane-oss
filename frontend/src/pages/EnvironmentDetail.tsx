// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useParams, Link } from 'react-router-dom';

interface EnvironmentDevice {
  id: number;
  hostname: string;
  asset_type: string;
  manufacturer?: string;
  model?: string;
  status: string;
  has_console: boolean;
  has_ipmi: boolean;
  console_link?: string;
  ipmi_link?: string;
  console_username?: string;
  console_password?: string;
  ipmi_username?: string;
  ipmi_password?: string;
}

interface Environment {
  id: string;
  name: string;
  ssh_link: string;
  ipmi_link: string;
}

const EnvironmentDetail: React.FC = () => {
  const { envId } = useParams<{ envId: string }>();
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [devices, setDevices] = useState<EnvironmentDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [powerCycling, setPowerCycling] = useState<{ [key: number]: boolean }>({});

  useEffect(() => {
    if (envId) {
      fetchEnvironmentDetails();
      fetchDevices();
    }
  }, [envId]);

  const fetchEnvironmentDetails = async () => {
    try {
      const response = await axios.get<Environment>(`${API_URL}/api/v1/environments/${envId}`);
      setEnvironment(response.data);
    } catch (err: any) {
      logger.error('Error fetching environment:', err);
      setError('Failed to load environment details');
    }
  };

  const fetchDevices = async () => {
    try {
      const response = await axios.get<EnvironmentDevice[]>(
        `${API_URL}/api/v1/environments/${envId}/devices`
      );
      setDevices(response.data);
      setError(null);
    } catch (err: any) {
      logger.error('Error fetching devices:', err);
      setError('Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const powerCycleDevice = async (deviceId: number, hostname: string) => {
    if (!window.confirm(`Are you sure you want to power cycle ${hostname}?`)) {
      return;
    }

    setPowerCycling((prev) => ({ ...prev, [deviceId]: true }));

    try {
      const response = await axios.post(
        `${API_URL}/api/v1/environments/devices/${deviceId}/power-cycle`
      );
      alert(response.data.message || 'Power cycle initiated');
    } catch (err: any) {
      logger.error('Error power cycling device:', err);
      alert('Failed to power cycle device');
    } finally {
      setPowerCycling((prev) => ({ ...prev, [deviceId]: false }));
    }
  };

  const openLink = (url: string, label: string) => {
    if (!url) {
      alert(`No ${label} link configured for this device`);
      return;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const getStatusBadgeClass = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower === 'active' || statusLower === 'deployed') {
      return 'badge-success';
    } else if (statusLower === 'maintenance') {
      return 'badge-warning';
    } else if (statusLower === 'failed') {
      return 'badge-danger';
    }
    return 'badge-secondary';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500 dark:text-gray-400">Loading devices...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/dev-troubleshooting" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300">
          ← Back to Environments
        </Link>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary mb-2">
          {environment?.name || envId?.toUpperCase()} Devices
        </h1>
        {environment && (
          <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
            <div>
              <span className="font-semibold">SSH:</span>{' '}
              <span className="font-mono">{environment.ssh_link}</span>
            </div>
            <div>
              <span className="font-semibold">IPMI:</span>{' '}
              <a
                href={environment.ipmi_link}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-blue-600 hover:text-blue-800"
              >
                {environment.ipmi_link}
              </a>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {devices.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 dark:text-gray-400 text-lg">
            No devices found for this environment.
          </p>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-2">
            Devices must have hostnames starting with {environment?.name || envId?.toUpperCase()}/
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {devices.map((device) => (
            <div key={device.id} className="card">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                {/* Device Info */}
                <div className="flex-grow">
                  <div className="flex items-center gap-3 mb-2">
                    <Link
                      to={`/assets/${device.id}`}
                      className="text-xl font-bold text-blue-600 hover:text-blue-800 transition"
                    >
                      {device.hostname}
                    </Link>
                    <span className={`badge ${getStatusBadgeClass(device.status)}`}>
                      {device.status}
                    </span>
                  </div>

                  <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
                    <div>
                      <span className="font-semibold">Type:</span> {device.asset_type}
                    </div>
                    {device.manufacturer && (
                      <div>
                        <span className="font-semibold">Manufacturer:</span> {device.manufacturer}
                      </div>
                    )}
                    {device.model && (
                      <div>
                        <span className="font-semibold">Model:</span> {device.model}
                      </div>
                    )}
                  </div>

                  {/* Credentials Display */}
                  {(device.has_console || device.has_ipmi) && (
                    <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 space-y-1">
                      {device.has_console && device.console_username && (
                        <div className="font-mono">
                          Console: {device.console_username} / {device.console_password ? '••••••••' : 'No password'}
                        </div>
                      )}
                      {device.has_ipmi && device.ipmi_username && (
                        <div className="font-mono">
                          IPMI: {device.ipmi_username} / {device.ipmi_password ? '••••••••' : 'No password'}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2 lg:flex-col lg:items-end">
                  {device.has_console && (
                    <button
                      onClick={() => openLink(device.console_link || '', 'Console')}
                      className="btn-secondary text-sm"
                      disabled={!device.console_link}
                    >
                      Console
                    </button>
                  )}

                  {device.has_ipmi && (
                    <button
                      onClick={() => openLink(device.ipmi_link || '', 'IPMI')}
                      className="btn-secondary text-sm"
                      disabled={!device.ipmi_link}
                    >
                      IPMI
                    </button>
                  )}

                  <button
                    onClick={() => powerCycleDevice(device.id, device.hostname)}
                    disabled={powerCycling[device.id]}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded transition text-sm"
                  >
                    {powerCycling[device.id] ? 'Cycling...' : 'Power Cycle'}
                  </button>

                  <Link
                    to={`/assets/${device.id}`}
                    className="btn-primary text-sm text-center"
                  >
                    View Asset
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EnvironmentDetail;
