// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';

interface DiagnosticResult {
  endpoint: string;
  status: 'success' | 'error' | 'pending';
  data?: any;
  error?: string;
}

const DiagnosticPage: React.FC = () => {
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [testing, setTesting] = useState(false);

  const endpoints = [
    { name: 'Health Check', url: '/health' },
    { name: 'Assets', url: '/api/v1/assets/' },
    { name: 'Datacenters', url: '/api/v1/locations/datacenters' },
    { name: 'Maintenance', url: '/api/v1/maintenance/' },
    { name: 'Dashboard Summary', url: '/api/v1/reports/dashboard/summary' },
  ];

  const runDiagnostics = async () => {
    setTesting(true);
    const newResults: DiagnosticResult[] = [];

    for (const endpoint of endpoints) {
      try {
        const response = await axios.get(`${API_URL}${endpoint.url}`);
        newResults.push({
          endpoint: endpoint.name,
          status: 'success',
          data: response.data,
        });
      } catch (error: any) {
        newResults.push({
          endpoint: endpoint.name,
          status: 'error',
          error: error.message || 'Unknown error',
        });
      }
    }

    setResults(newResults);
    setTesting(false);
  };

  useEffect(() => {
    runDiagnostics();
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-primary mb-8">
        Frontend Diagnostics
      </h1>

      <div className="card mb-6">
        <h2 className="text-xl font-bold text-primary mb-4">Configuration</h2>
        <div className="space-y-2 font-mono text-sm text-primary">
          <div className="flex gap-4">
            <span className="font-semibold">API URL:</span>
            <span className="text-blue-600 dark:text-blue-400">{API_URL}</span>
          </div>
          <div className="flex gap-4">
            <span className="font-semibold">Environment:</span>
            <span className="text-blue-600 dark:text-blue-400">{process.env.NODE_ENV}</span>
          </div>
        </div>
        <button
          onClick={runDiagnostics}
          disabled={testing}
          className="btn-primary mt-4"
        >
          {testing ? 'Testing...' : 'Rerun Tests'}
        </button>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">
          Endpoint Tests
        </h2>
        <div className="space-y-4">
          {results.map((result, index) => (
            <div
              key={index}
              className={`border-l-4 p-4 rounded ${result.status === 'success'
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-500 dark:border-green-400'
                  : 'bg-red-50 dark:bg-red-900/20 border-red-500 dark:border-red-400'
                }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-primary">
                  {result.endpoint}
                </h3>
                <span
                  className={`badge ${result.status === 'success'
                      ? 'badge-success'
                      : 'badge-danger'
                    }`}
                >
                  {result.status}
                </span>
              </div>

              {result.status === 'success' ? (
                <div className="mt-2">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Response preview:</p>
                  <pre className="bg-subtle dark:text-gray-300 p-3 rounded text-xs overflow-auto max-h-40 text-primary">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="mt-2">
                  <p className="text-sm text-red-600 dark:text-red-400 font-semibold">Error:</p>
                  <p className="text-sm text-red-700 dark:text-red-300">{result.error}</p>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <p>Common causes:</p>
                    <ul className="list-disc ml-4 mt-1">
                      <li>Backend not running (check: docker-compose ps)</li>
                      <li>CORS configuration issue</li>
                      <li>Network connectivity problem</li>
                      <li>Backend crashed (check: docker-compose logs backend)</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card mt-6">
        <h2 className="text-xl font-bold text-primary mb-4">
          Troubleshooting Steps
        </h2>
        <ol className="list-decimal ml-6 space-y-2 text-primary">
          <li>
            Check if backend is running:{' '}
            <code className="bg-subtle dark:text-gray-300 px-2 py-1 rounded text-primary">
              docker-compose ps backend
            </code>
          </li>
          <li>
            Test backend directly:{' '}
            <code className="bg-subtle dark:text-gray-300 px-2 py-1 rounded text-primary">
              curl http://localhost:8000/health
            </code>
          </li>
          <li>
            Check backend logs:{' '}
            <code className="bg-subtle dark:text-gray-300 px-2 py-1 rounded text-primary">
              docker-compose logs backend
            </code>
          </li>
          <li>
            Open browser console (F12) and check for errors
          </li>
          <li>
            Verify CORS headers in Network tab
          </li>
        </ol>
      </div>
    </div>
  );
};

export default DiagnosticPage;
