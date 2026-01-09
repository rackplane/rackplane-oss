// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { Link } from 'react-router-dom';

interface Environment {
  id: string;
  name: string;
  ssh_link: string;
  ipmi_link: string;
  ssh_username?: string;
  ssh_password?: string;
  ipmi_username?: string;
  ipmi_password?: string;
}

interface PingResult {
  success: boolean;
  output: string;
  error?: string;
}

const EnvironmentTroubleshooting: React.FC = () => {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingEnv, setEditingEnv] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Environment>({
    id: '',
    name: '',
    ssh_link: '',
    ipmi_link: '',
    ssh_username: '',
    ssh_password: '',
    ipmi_username: '',
    ipmi_password: '',
  });
  const [pingResults, setPingResults] = useState<{ [key: string]: PingResult | null }>({});
  const [pinging, setPinging] = useState<{ [key: string]: boolean }>({});
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    fetchEnvironments();
  }, []);

  const fetchEnvironments = async () => {
    try {
      const response = await axios.get<Environment[]>(`${API_URL}/api/v1/environments/`);
      setEnvironments(response.data);
      setError(null);
    } catch (err: any) {
      logger.error('Error fetching environments:', err);
      setError('Failed to load environments');
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (env: Environment) => {
    setEditingEnv(env.id);
    setEditValues({ ...env });
  };

  const cancelEdit = () => {
    setEditingEnv(null);
  };

  const saveEdit = async (envId: string) => {
    try {
      await axios.put(`${API_URL}/api/v1/environments/${envId}`, {
        ssh_link: editValues.ssh_link,
        ipmi_link: editValues.ipmi_link,
        ssh_username: editValues.ssh_username,
        ssh_password: editValues.ssh_password,
        ipmi_username: editValues.ipmi_username,
        ipmi_password: editValues.ipmi_password,
      });
      await fetchEnvironments();
      setEditingEnv(null);
      setError(null);
    } catch (err: any) {
      logger.error('Error updating environment:', err);
      setError('Failed to update environment');
    }
  };

  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      logger.error('Failed to copy:', err);
    }
  };

  const pingServer = async (envId: string, type: 'server' | 'ipmi') => {
    const key = `${envId}-${type}`;
    setPinging((prev) => ({ ...prev, [key]: true }));
    setPingResults((prev) => ({ ...prev, [key]: null }));

    try {
      const endpoint = type === 'server' ? 'ping' : 'ping-ipmi';
      const response = await axios.post<PingResult>(
        `${API_URL}/api/v1/environments/${envId}/${endpoint}`
      );
      setPingResults((prev) => ({ ...prev, [key]: response.data }));
    } catch (err: any) {
      logger.error(`Error pinging ${type}:`, err);
      setPingResults((prev) => ({
        ...prev,
        [key]: { success: false, output: '', error: 'Failed to ping' },
      }));
    } finally {
      setPinging((prev) => ({ ...prev, [key]: false }));
    }
  };

  const powerCycle = async (envId: string) => {
    if (!window.confirm('Are you sure you want to power cycle this environment?')) {
      return;
    }

    try {
      const response = await axios.post(`${API_URL}/api/v1/environments/${envId}/power-cycle`);
      alert(response.data.message || 'Power cycle initiated');
    } catch (err: any) {
      logger.error('Error power cycling:', err);
      alert('Failed to power cycle environment');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500 dark:text-gray-400">Loading environments...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold text-primary mb-8">
        DEV Troubleshooting
      </h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {environments.map((env) => {
          const isEditing = editingEnv === env.id;
          const serverPingKey = `${env.id}-server`;
          const ipmiPingKey = `${env.id}-ipmi`;

          return (
            <div key={env.id} className="card">
              <div className="flex justify-between items-start mb-4">
                <Link
                  to={`/environment/${env.id}`}
                  className="text-2xl font-bold text-blue-600 hover:text-blue-800 transition"
                >
                  {env.name}
                </Link>
                {!isEditing && (
                  <button
                    onClick={() => startEdit(env)}
                    className="btn-secondary text-sm"
                  >
                    Edit
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
                {/* SSH Section */}
                <div className="border rounded-lg p-4 bg-section-card">
                  <h3 className="text-lg font-semibold text-primary mb-3">SSH Access</h3>

                  <div className="mb-3">
                    <label className="block text-sm font-semibold text-primary mb-1">
                      SSH Link
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editValues.ssh_link}
                        onChange={(e) =>
                          setEditValues({ ...editValues, ssh_link: e.target.value })
                        }
                        className="input w-full"
                      />
                    ) : (
                      <div className="flex gap-2">
                        <div className="font-mono text-sm bg-card p-2 rounded border flex-grow">
                          {env.ssh_link}
                        </div>
                        <button
                          onClick={() => copyToClipboard(env.ssh_link, `${env.id}-ssh-link`)}
                          className="btn-secondary text-xs px-2"
                          title="Copy SSH link"
                        >
                          {copiedField === `${env.id}-ssh-link` ? '✓' : '📋'}
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-semibold text-primary mb-1">
                        Username
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.ssh_username || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, ssh_username: e.target.value })
                          }
                          className="input w-full"
                          placeholder="SSH username"
                        />
                      ) : (
                        <div className="flex gap-2">
                          <div className="font-mono text-sm bg-card p-2 rounded border flex-grow">
                            {env.ssh_username || '—'}
                          </div>
                          {env.ssh_username && (
                            <button
                              onClick={() => copyToClipboard(env.ssh_username!, `${env.id}-ssh-user`)}
                              className="btn-secondary text-xs px-2"
                              title="Copy username"
                            >
                              {copiedField === `${env.id}-ssh-user` ? '✓' : '📋'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-primary mb-1">
                        Password
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.ssh_password || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, ssh_password: e.target.value })
                          }
                          className="input w-full"
                          placeholder="SSH password"
                        />
                      ) : (
                        <div className="flex gap-2">
                          <div className="font-mono text-sm bg-card p-2 rounded border flex-grow">
                            {env.ssh_password || '—'}
                          </div>
                          {env.ssh_password && (
                            <button
                              onClick={() => copyToClipboard(env.ssh_password!, `${env.id}-ssh-pass`)}
                              className="btn-secondary text-xs px-2"
                              title="Copy password"
                            >
                              {copiedField === `${env.id}-ssh-pass` ? '✓' : '📋'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* IPMI Section */}
                <div className="border rounded-lg p-4 bg-section-card">
                  <h3 className="text-lg font-semibold text-primary mb-3">IPMI Access</h3>

                  <div className="mb-3">
                    <label className="block text-sm font-semibold text-primary mb-1">
                      IPMI Link
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editValues.ipmi_link}
                        onChange={(e) =>
                          setEditValues({ ...editValues, ipmi_link: e.target.value })
                        }
                        className="input w-full"
                      />
                    ) : (
                      <div className="flex gap-2">
                        <a
                          href={env.ipmi_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-sm bg-card p-2 rounded border flex-grow text-blue-600 hover:text-blue-800 transition"
                        >
                          {env.ipmi_link}
                        </a>
                        <button
                          onClick={() => copyToClipboard(env.ipmi_link, `${env.id}-ipmi-link`)}
                          className="btn-secondary text-xs px-2"
                          title="Copy IPMI link"
                        >
                          {copiedField === `${env.id}-ipmi-link` ? '✓' : '📋'}
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-semibold text-primary mb-1">
                        Username
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.ipmi_username || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, ipmi_username: e.target.value })
                          }
                          className="input w-full"
                          placeholder="IPMI username"
                        />
                      ) : (
                        <div className="flex gap-2">
                          <div className="font-mono text-sm bg-card p-2 rounded border flex-grow">
                            {env.ipmi_username || '—'}
                          </div>
                          {env.ipmi_username && (
                            <button
                              onClick={() => copyToClipboard(env.ipmi_username!, `${env.id}-ipmi-user`)}
                              className="btn-secondary text-xs px-2"
                              title="Copy username"
                            >
                              {copiedField === `${env.id}-ipmi-user` ? '✓' : '📋'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-primary mb-1">
                        Password
                      </label>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.ipmi_password || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, ipmi_password: e.target.value })
                          }
                          className="input w-full"
                          placeholder="IPMI password"
                        />
                      ) : (
                        <div className="flex gap-2">
                          <div className="font-mono text-sm bg-card p-2 rounded border flex-grow">
                            {env.ipmi_password || '—'}
                          </div>
                          {env.ipmi_password && (
                            <button
                              onClick={() => copyToClipboard(env.ipmi_password!, `${env.id}-ipmi-pass`)}
                              className="btn-secondary text-xs px-2"
                              title="Copy password"
                            >
                              {copiedField === `${env.id}-ipmi-pass` ? '✓' : '📋'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              {isEditing ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => saveEdit(env.id)}
                    className="btn-primary"
                  >
                    Save Changes
                  </button>
                  <button onClick={cancelEdit} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => pingServer(env.id, 'server')}
                    disabled={pinging[serverPingKey]}
                    className="btn-secondary"
                  >
                    {pinging[serverPingKey] ? 'Pinging...' : 'Ping Server'}
                  </button>
                  <button
                    onClick={() => pingServer(env.id, 'ipmi')}
                    disabled={pinging[ipmiPingKey]}
                    className="btn-secondary"
                  >
                    {pinging[ipmiPingKey] ? 'Pinging...' : 'Ping IPMI'}
                  </button>
                  <button
                    onClick={() => powerCycle(env.id)}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded transition"
                  >
                    Power Cycle
                  </button>
                  <Link
                    to={`/environment/${env.id}`}
                    className="btn-primary"
                  >
                    View Devices
                  </Link>
                </div>
              )}

              {/* Ping Results */}
              {(pingResults[serverPingKey] || pingResults[ipmiPingKey]) && (
                <div className="mt-4 space-y-2">
                  {pingResults[serverPingKey] && (
                    <div
                      className={`border-l-4 p-3 rounded text-sm ${pingResults[serverPingKey]!.success
                          ? 'bg-green-50 border-green-500'
                          : 'bg-red-50 border-red-500'
                        }`}
                    >
                      <div className="font-semibold mb-1">
                        Server Ping: {pingResults[serverPingKey]!.success ? '✓ Success' : '✗ Failed'}
                      </div>
                      {pingResults[serverPingKey]!.error && (
                        <div className="text-red-600">{pingResults[serverPingKey]!.error}</div>
                      )}
                      {pingResults[serverPingKey]!.output && (
                        <pre className="mt-2 text-xs overflow-auto max-h-32 bg-card p-2 rounded">
                          {pingResults[serverPingKey]!.output}
                        </pre>
                      )}
                    </div>
                  )}

                  {pingResults[ipmiPingKey] && (
                    <div
                      className={`border-l-4 p-3 rounded text-sm ${pingResults[ipmiPingKey]!.success
                          ? 'bg-green-50 border-green-500'
                          : 'bg-red-50 border-red-500'
                        }`}
                    >
                      <div className="font-semibold mb-1">
                        IPMI Ping: {pingResults[ipmiPingKey]!.success ? '✓ Success' : '✗ Failed'}
                      </div>
                      {pingResults[ipmiPingKey]!.error && (
                        <div className="text-red-600">{pingResults[ipmiPingKey]!.error}</div>
                      )}
                      {pingResults[ipmiPingKey]!.output && (
                        <pre className="mt-2 text-xs overflow-auto max-h-32 bg-card p-2 rounded">
                          {pingResults[ipmiPingKey]!.output}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EnvironmentTroubleshooting;
