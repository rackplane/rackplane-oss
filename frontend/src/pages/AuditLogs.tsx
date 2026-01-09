// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Audit Logs Viewer Page
 * 
 * Displays a comprehensive audit trail of all system changes.
 * 
 * Features:
 * - View all audit log entries (who did what, when)
 * - Filter by user, table, action, date range
 * - Search through change details
 * - Expandable rows showing before/after comparisons
 * - Export filtered results to CSV
 * 
 * Permissions:
 * - TENANT_ADMIN: Can view logs for their tenant only
 * - SUPER_ADMIN: Can view logs for all tenants
 * - USER and READ_ONLY: Cannot access this page
 * 
 * @module AuditLogs
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useAuth } from '../contexts/AuthContext';
import { parseUserAgent, getUserAgentIcon, getUserAgentDisplayName } from '../utils/userAgentParser';

/**
 * Audit log entry interface
 * Matches the backend AuditLogResponse schema
 */
interface AuditLog {
  id: number;
  table_name: string;
  record_id: number | null;
  action: string;
  user_id: number | null;
  username: string | null;
  tenant_id: number | null;
  before_values: Record<string, any> | null;
  after_values: Record<string, any> | null;
  changes: Record<string, any> | null;
  ip_address: string | null;
  user_agent: string | null;
  api_key_id: number | null;
  api_key_label: string | null;
  notes: string | null;
  created_at: string;
}

interface AuditLogListResponse {
  total: number;
  limit: number;
  offset: number;
  logs: AuditLog[];
}

/**
 * Main AuditLogs component
 * 
 * Manages state for:
 * - logs: Array of audit log entries to display
 * - loading: Loading state indicator
 * - total: Total number of logs (for pagination)
 * - page: Current page number
 * - filters: Active filter values (user, table, action, date range)
 * - expandedRow: ID of currently expanded row (for showing details)
 */
const AuditLogs: React.FC = () => {
  const { isTenantAdmin } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [filters, setFilters] = useState({
    username: '',
    table_name: '',
    action: '',
    start_date: '',
    end_date: ''
  });

  const pageSize = 50;

  /**
   * Fetch audit logs when page or filters change
   */
  useEffect(() => {
    if (isTenantAdmin) {
      fetchLogs();
    }
  }, [page, filters, isTenantAdmin]);

  /**
   * Fetch audit logs from the API
   * Applies current filters and pagination
   */
  const fetchLogs = async () => {
    if (!isTenantAdmin) {
      setError('Access denied. Tenant admin or super admin privileges required.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.append('limit', String(pageSize));
      params.append('offset', String((page - 1) * pageSize));

      if (filters.username) {
        params.append('username', filters.username);
      }
      if (filters.table_name) {
        params.append('table_name', filters.table_name);
      }
      if (filters.action) {
        params.append('action', filters.action);
      }
      if (filters.start_date) {
        params.append('start_date', filters.start_date);
      }
      if (filters.end_date) {
        params.append('end_date', filters.end_date);
      }

      // Add trailing slash to match FastAPI route definition and avoid 307 redirect
      const url = `${API_URL}/api/v1/audit-logs/?${params.toString()}`;
      logger.debug('Fetching audit logs from:', url);
      logger.debug('API_URL:', API_URL);

      const response = await axios.get<AuditLogListResponse>(url, {
        timeout: 30000, // 30 second timeout
      });

      // Verify response structure
      if (!response.data) {
        throw new Error('Invalid response format from server');
      }

      // Handle both direct array response (legacy) and paginated response (new)
      if (Array.isArray(response.data)) {
        // Legacy format - direct array
        setLogs(response.data);
        setTotal(response.data.length);
      } else if (response.data.logs && Array.isArray(response.data.logs)) {
        // New format - paginated response
        setLogs(response.data.logs);
        setTotal(response.data.total || response.data.logs.length);
      } else {
        throw new Error('Unexpected response format from server');
      }
    } catch (error: any) {
      logger.error('Failed to fetch audit logs:', error);

      // Handle different error types for better diagnostics
      let errorMessage = 'Failed to load audit logs';

      if (error.response) {
        // Server responded with an error status
        errorMessage = error.response.data?.detail || error.response.statusText || `Server error (${error.response.status})`;

        // If it's a 403, suggest re-login
        if (error.response.status === 403) {
          errorMessage = `${errorMessage}. You may need to log out and log back in to refresh your permissions.`;
        } else if (error.response.status === 404) {
          errorMessage = 'Audit logs endpoint not found. The audit_logs table may not exist.';
        }
      } else if (error.request) {
        // Request was made but no response received (network error)
        errorMessage = 'Network error: Could not reach the server. Please check your connection and try again.';
        logger.error('Network error details:', {
          url: error.config?.url,
          method: error.config?.method,
          message: error.message
        });
      } else {
        // Something else happened
        errorMessage = error.message || 'An unexpected error occurred';
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Export filtered audit logs to CSV
   * Triggers a download of the current filtered results
   */
  const handleExport = async () => {
    try {
      const params = new URLSearchParams();

      if (filters.username) {
        params.append('username', filters.username);
      }
      if (filters.table_name) {
        params.append('table_name', filters.table_name);
      }
      if (filters.action) {
        params.append('action', filters.action);
      }
      if (filters.start_date) {
        params.append('start_date', filters.start_date);
      }
      if (filters.end_date) {
        params.append('end_date', filters.end_date);
      }

      // Trigger download
      window.location.href = `${API_URL}/api/v1/audit-logs/export?${params.toString()}`;
    } catch (error: any) {
      logger.error('Failed to export audit logs:', error);
      setError('Failed to export audit logs');
    }
  };

  /**
   * Clear all filters and reset to page 1
   */
  const clearFilters = () => {
    setFilters({
      username: '',
      table_name: '',
      action: '',
      start_date: '',
      end_date: ''
    });
    setPage(1);
  };

  /**
   * Get action badge color class
   */
  const getActionBadgeClass = (action: string): string => {
    switch (action.toLowerCase()) {
      case 'create':
        return 'badge badge-success';
      case 'update':
        return 'badge badge-info';
      case 'delete':
        return 'badge badge-danger';
      default:
        return 'badge badge-info';
    }
  };

  /**
   * Format date for display
   */
  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  /**
   * Get unique usernames from logs for filter dropdown
   */
  const getUniqueUsernames = (): string[] => {
    const usernames = new Set<string>();
    logs.forEach(log => {
      if (log.username) {
        usernames.add(log.username);
      }
    });
    return Array.from(usernames).sort();
  };

  /**
   * Get unique table names from logs for filter dropdown
   */
  const getUniqueTableNames = (): string[] => {
    const tables = new Set<string>();
    logs.forEach(log => {
      if (log.table_name) {
        tables.add(log.table_name);
      }
    });
    return Array.from(tables).sort();
  };

  // Access denied message
  if (!isTenantAdmin) {
    return (
      <div className="min-h-screen bg-page flex items-center justify-center p-4">
        <div className="text-center max-w-md mx-auto p-6 bg-card rounded-lg shadow-xl">
          <h1 className="text-4xl font-bold text-primary mb-4">Access Denied</h1>
          <p className="text-gray-500 dark:text-gray-400 mb-8">
            This page requires tenant administrator or super administrator privileges.
            Please contact your system administrator if you need access.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Audit Logs</h1>
        <button
          onClick={handleExport}
          className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-hover transition"
        >
          📥 Export CSV
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="text-red-800 dark:text-red-200 font-semibold">Error Loading Audit Logs</div>
          <div className="text-red-600 dark:text-red-300 text-sm mt-1">{error}</div>
          {(error.includes('403') || error.includes('permission') || error.includes('access') || error.includes('denied')) ? (
            <div className="text-red-600 dark:text-red-300 text-sm mt-2">
              <strong>Solution:</strong> Log out and log back in to refresh your authentication token with updated permissions.
            </div>
          ) : null}
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 p-4 bg-card rounded-lg shadow">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* Username Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              User
            </label>
            <input
              type="text"
              value={filters.username}
              onChange={(e) => setFilters({ ...filters, username: e.target.value })}
              placeholder="Filter by username"
              className="input w-full"
            />
          </div>

          {/* Table Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Table
            </label>
            <select
              value={filters.table_name}
              onChange={(e) => setFilters({ ...filters, table_name: e.target.value })}
              className="input w-full"
            >
              <option value="">All Tables</option>
              {getUniqueTableNames().map(table => (
                <option key={table} value={table}>{table}</option>
              ))}
            </select>
          </div>

          {/* Action Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Action
            </label>
            <select
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="input w-full"
            >
              <option value="">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
            </select>
          </div>

          {/* Start Date Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Start Date
            </label>
            <input
              type="datetime-local"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              className="input w-full"
            />
          </div>

          {/* End Date Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              End Date
            </label>
            <input
              type="datetime-local"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              className="input w-full"
            />
          </div>
        </div>

        {/* Clear Filters Button */}
        <div className="mt-4">
          <button
            onClick={clearFilters}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Results Summary */}
      <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
        Showing {logs.length > 0 ? (page - 1) * pageSize + 1 : 0} - {Math.min(page * pageSize, total)} of {total} results
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-8">
          <div className="text-xl text-gray-600 dark:text-gray-400">Loading audit logs...</div>
        </div>
      )}

      {/* Audit Logs Table */}
      {!loading && !error && logs.length === 0 && (
        <div className="text-center py-8 bg-card rounded-lg shadow">
          <div className="text-xl text-gray-500 dark:text-gray-400">No audit logs found</div>
          <div className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            Try adjusting your filters or check back later.
          </div>
        </div>
      )}

      {!loading && logs.length > 0 && (
        <div className="bg-card rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-table-header">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Table
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Record ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Device
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map((log) => (
                  <React.Fragment key={log.id}>
                    <tr
                      className={`hover:bg-table-row-hover cursor-pointer ${expandedRow === log.id ? 'bg-table-row-hover' : ''
                        }`}
                      onClick={() => setExpandedRow(expandedRow === log.id ? null : log.id)}
                    >
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                        <div>
                          {log.username || `User #${log.user_id}`}
                          {log.api_key_id && (
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              via {log.api_key_label || `Relay Token #${log.api_key_id}`}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getActionBadgeClass(log.action)}`}>
                          {log.action.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                        {log.table_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                        {log.record_id ? `#${log.record_id}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400" title={getUserAgentDisplayName(log.user_agent) + (log.ip_address ? ` - ${log.ip_address}` : '')}>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getUserAgentIcon(log.user_agent)}</span>
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            {parseUserAgent(log.user_agent).deviceType}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {expandedRow === log.id ? '▼' : '►'}
                      </td>
                    </tr>

                    {/* Expanded Row Details */}
                    {expandedRow === log.id && (
                      <tr>
                        <td colSpan={7} className="px-4 py-4 bg-subtle-card">
                          <div className="space-y-4">
                            {/* IP Address and User Agent */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300">IP Address:</strong>
                                <span className="ml-2 text-gray-600 dark:text-gray-400">
                                  {log.ip_address || 'N/A'}
                                </span>
                              </div>
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300">Device & Browser:</strong>
                                <div className="mt-1">
                                  <span className="text-2xl mr-2">{getUserAgentIcon(log.user_agent)}</span>
                                  <span className="text-gray-600 dark:text-gray-400 text-sm font-medium">
                                    {getUserAgentDisplayName(log.user_agent)}
                                  </span>
                                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-500">
                                    ({parseUserAgent(log.user_agent).deviceType})
                                  </span>
                                </div>
                                {log.user_agent && (
                                  <details className="mt-2">
                                    <summary className="text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
                                      Show full user agent string
                                    </summary>
                                    <pre className="mt-1 text-xs text-gray-600 dark:text-gray-400 bg-subtle-card p-2 rounded overflow-auto">
                                      {log.user_agent}
                                    </pre>
                                  </details>
                                )}
                              </div>
                            </div>

                            {/* Changes Table (for UPDATE actions) */}
                            {log.action === 'update' && log.changes && Object.keys(log.changes).length > 0 && (
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300 block mb-2">Changes:</strong>
                                <div className="overflow-x-auto">
                                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                    <thead className="bg-table-header">
                                      <tr>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300">
                                          Field
                                        </th>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300">
                                          Old Value
                                        </th>
                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300">
                                          New Value
                                        </th>
                                      </tr>
                                    </thead>
                                    <tbody className="bg-card divide-y divide-gray-200 dark:divide-gray-700">
                                      {Object.entries(log.changes).map(([field, changeValue]) => {
                                        // Handle both formats: {old, new} object or direct value (backward compatibility)
                                        let oldValue: any;
                                        let newValue: any;

                                        if (changeValue && typeof changeValue === 'object' && 'old' in changeValue && 'new' in changeValue) {
                                          // New format: {old: 5, new: 10}
                                          oldValue = changeValue.old;
                                          newValue = changeValue.new;
                                        } else {
                                          // Legacy format: direct value (fallback to before_values)
                                          newValue = changeValue;
                                          oldValue = log.before_values?.[field];
                                        }

                                        return (
                                          <tr key={field}>
                                            <td className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                                              {field}
                                            </td>
                                            <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                                              {oldValue !== undefined && oldValue !== null
                                                ? typeof oldValue === 'object' ? JSON.stringify(oldValue) : String(oldValue)
                                                : '-'}
                                            </td>
                                            <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                                              {newValue !== undefined && newValue !== null
                                                ? typeof newValue === 'object' ? JSON.stringify(newValue) : String(newValue)
                                                : '-'}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* After Values (for CREATE actions) */}
                            {log.action === 'create' && log.after_values && (
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300 block mb-2">Created Values:</strong>
                                <pre className="bg-subtle-card p-3 rounded overflow-auto text-sm">
                                  {JSON.stringify(log.after_values, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Before Values (for DELETE actions) */}
                            {log.action === 'delete' && log.before_values && (
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300 block mb-2">Deleted Values:</strong>
                                <pre className="bg-subtle-card p-3 rounded overflow-auto text-sm">
                                  {JSON.stringify(log.before_values, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Notes */}
                            {log.notes && (
                              <div>
                                <strong className="text-gray-700 dark:text-gray-300">Notes:</strong>
                                <p className="mt-1 text-gray-600 dark:text-gray-400">{log.notes}</p>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {!loading && total > pageSize && (
        <div className="mt-6 flex justify-between items-center">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Previous
          </button>
          <span className="text-gray-600 dark:text-gray-400">
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(total / pageSize)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;

