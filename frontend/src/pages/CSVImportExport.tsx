// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface ImportResult {
  success: boolean;
  imported_count: number;
  skipped_count: number;
  errors: string[];
}

interface PreviewItem {
  row_number: number;
  selected: boolean;
  valid: boolean;
  errors: string[];
  warnings: string[];
  data: {
    asset_tag: string;
    serial_number: string;
    asset_type: string;
    manufacturer: string;
    model: string;
    status: string;
    hostname: string;
    description: string;
    datacenter_id?: number;
    datacenter_name?: string;
    datacenter_code?: string;
    rack_id?: number;
    rack_name?: string;
    rack_code?: string;
    rack_position_start?: string;
    rack_position_end?: string;
  };
}

interface PreviewResult {
  success: boolean;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  items: PreviewItem[];
}

const CSVImportExport: React.FC = () => {
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [skipErrors, setSkipErrors] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [exportFilters, setExportFilters] = useState({
    asset_type: '',
    status: ''
  });

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const params = new URLSearchParams();
      if (exportFilters.asset_type) {
        params.append('asset_type', exportFilters.asset_type);
      }
      if (exportFilters.status) {
        params.append('status', exportFilters.status);
      }

      const response = await axios.get(`${API_URL}/api/v1/csv/export?${params.toString()}`, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `assets_export_${timestamp}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      logger.error('Export error:', error);
      alert(`Export failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        alert('Please select a CSV file');
        return;
      }
      setSelectedFile(file);
      setImportResult(null);
      setPreviewResult(null);
      setShowPreview(false);

      // Automatically preview the file
      await handlePreview(file);
    }
  };

  const handlePreview = async (file: File) => {
    setPreviewLoading(true);
    setPreviewResult(null);
    setShowPreview(false);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `${API_URL}/api/v1/csv/preview`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setPreviewResult(response.data);
      setShowPreview(true);
    } catch (error: any) {
      logger.error('Preview error:', error);
      alert(`Preview failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const toggleItem = (rowNumber: number) => {
    if (!previewResult) return;

    const updatedItems = previewResult.items.map(item =>
      item.row_number === rowNumber
        ? { ...item, selected: !item.selected }
        : item
    );

    setPreviewResult({
      ...previewResult,
      items: updatedItems
    });
  };

  const toggleAll = () => {
    if (!previewResult) return;

    const allSelected = previewResult.items.every(item => item.selected);
    const updatedItems = previewResult.items.map(item => ({
      ...item,
      selected: !allSelected
    }));

    setPreviewResult({
      ...previewResult,
      items: updatedItems
    });
  };

  const toggleValidOnly = () => {
    if (!previewResult) return;

    const updatedItems = previewResult.items.map(item => ({
      ...item,
      selected: item.valid
    }));

    setPreviewResult({
      ...previewResult,
      items: updatedItems
    });
  };

  const handleImport = async () => {
    if (!selectedFile) {
      alert('Please select a CSV file to import');
      return;
    }

    // Get selected row numbers
    const selectedRowNumbers = previewResult?.items
      .filter(item => item.selected)
      .map(item => item.row_number)
      .join(',');

    if (!selectedRowNumbers) {
      alert('Please select at least one item to import');
      return;
    }

    setImportLoading(true);
    setImportProgress(0);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setImportProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const params = new URLSearchParams();
      params.append('skip_errors', skipErrors.toString());
      if (selectedRowNumbers) {
        params.append('selected_rows', selectedRowNumbers);
      }

      const response = await axios.post(
        `${API_URL}/api/v1/csv/import?${params.toString()}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              setImportProgress(percentCompleted);
            }
          },
        }
      );

      clearInterval(progressInterval);
      setImportProgress(100);
      setImportResult(response.data);

      // Clear file selection after successful import
      if (response.data.success) {
        setSelectedFile(null);
        setPreviewResult(null);
        setShowPreview(false);
        const fileInput = document.getElementById('csv-file-input') as HTMLInputElement;
        if (fileInput) {
          fileInput.value = '';
        }
      }
    } catch (error: any) {
      logger.error('Import error:', error);
      setImportProgress(0);
      setImportResult({
        success: false,
        imported_count: 0,
        skipped_count: 0,
        errors: [error.response?.data?.detail || error.message || 'Import failed'],
      });
    } finally {
      setImportLoading(false);
    }
  };

  const selectedCount = previewResult?.items.filter(item => item.selected).length || 0;

  return (
    <div>
      <h1 className="text-3xl font-bold text-primary mb-8">CSV Import / Export</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Export Section */}
        <div className="card">
          <h2 className="text-xl font-bold text-primary mb-4">Export Assets to CSV</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Download all assets or filter by type and status.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Asset Type (optional)
              </label>
              <input
                type="text"
                value={exportFilters.asset_type}
                onChange={(e) => setExportFilters({ ...exportFilters, asset_type: e.target.value })}
                placeholder="e.g., server_device, network_device"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Status (optional)
              </label>
              <select
                value={exportFilters.status}
                onChange={(e) => setExportFilters({ ...exportFilters, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="deployed">Deployed</option>
                <option value="in_storage">In Storage</option>
                <option value="maintenance">Maintenance</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <button
              onClick={handleExport}
              disabled={exportLoading}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exportLoading ? (
                <span className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Exporting...
                </span>
              ) : (
                '📥 Download CSV Export'
              )}
            </button>
          </div>
        </div>

        {/* Import Section */}
        <div className="card">
          <h2 className="text-xl font-bold text-primary mb-4">Import Assets from CSV</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Upload a CSV file to import assets. Required fields: asset_tag, serial_number, asset_type.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                CSV File
              </label>
              <input
                id="csv-file-input"
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileSelect}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {selectedFile && (
                <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                </div>
              )}
            </div>

            {previewLoading && (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Previewing CSV...</p>
              </div>
            )}

            {showPreview && previewResult && (
              <div className="border border-default rounded-lg p-4 bg-section-card">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h3 className="font-semibold text-primary">Preview ({previewResult.total_rows} rows)</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {previewResult.valid_rows} valid, {previewResult.invalid_rows} invalid
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={toggleAll}
                      className="text-sm px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded"
                    >
                      {previewResult.items.every(item => item.selected) ? 'Deselect All' : 'Select All'}
                    </button>
                    <button
                      onClick={toggleValidOnly}
                      className="text-sm px-3 py-1 bg-blue-100 hover:bg-blue-200 rounded"
                    >
                      Select Valid Only
                    </button>
                  </div>
                </div>

                <div className="max-h-96 overflow-y-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-200 sticky top-0">
                      <tr>
                        <th className="px-2 py-2 text-left">
                          <input
                            type="checkbox"
                            checked={previewResult.items.every(item => item.selected)}
                            onChange={toggleAll}
                            className="rounded"
                          />
                        </th>
                        <th className="px-2 py-2 text-left">Row</th>
                        <th className="px-2 py-2 text-left">Asset Tag</th>
                        <th className="px-2 py-2 text-left">Serial</th>
                        <th className="px-2 py-2 text-left">Type</th>
                        <th className="px-2 py-2 text-left">Manufacturer</th>
                        <th className="px-2 py-2 text-left">Model</th>
                        <th className="px-2 py-2 text-left">Rack</th>
                        <th className="px-2 py-2 text-left">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewResult.items.map((item) => (
                        <tr
                          key={item.row_number}
                          className={`border-b ${item.selected ? 'bg-blue-50' : ''} ${!item.valid ? 'bg-red-50' : ''
                            }`}
                        >
                          <td className="px-2 py-2">
                            <input
                              type="checkbox"
                              checked={item.selected}
                              onChange={() => toggleItem(item.row_number)}
                              disabled={!item.valid}
                              className="rounded"
                            />
                          </td>
                          <td className="px-2 py-2">{item.row_number}</td>
                          <td className="px-2 py-2 font-mono text-xs">{item.data.asset_tag || '-'}</td>
                          <td className="px-2 py-2 font-mono text-xs">{item.data.serial_number || '-'}</td>
                          <td className="px-2 py-2">{item.data.asset_type || '-'}</td>
                          <td className="px-2 py-2">{item.data.manufacturer || '-'}</td>
                          <td className="px-2 py-2">{item.data.model || '-'}</td>
                          <td className="px-2 py-2">
                            {item.data.rack_name || item.data.rack_code ? (
                              <span className="text-xs">
                                {item.data.rack_name || item.data.rack_code}
                                {item.data.rack_position_start && ` (U${item.data.rack_position_start})`}
                                {item.data.datacenter_name && (
                                  <span className="text-gray-500 dark:text-gray-400 block">{item.data.datacenter_name}</span>
                                )}
                              </span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                          <td className="px-2 py-2">
                            {item.valid ? (
                              <span className="text-green-600">✓</span>
                            ) : (
                              <span className="text-red-600" title={item.errors.join(', ')}>✗</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {previewResult.items.some(item => !item.valid) && (
                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-sm font-semibold text-yellow-800 mb-2">Validation Errors:</p>
                    <div className="max-h-32 overflow-y-auto text-xs">
                      {previewResult.items
                        .filter(item => !item.valid)
                        .map(item => (
                          <div key={item.row_number} className="mb-1">
                            <span className="font-mono">Row {item.row_number}:</span>{' '}
                            {item.errors.join(', ')}
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                  <strong>{selectedCount}</strong> of {previewResult.total_rows} items selected for import
                </div>
              </div>
            )}

            <div className="flex items-center">
              <input
                type="checkbox"
                id="skip-errors"
                checked={skipErrors}
                onChange={(e) => setSkipErrors(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="skip-errors" className="ml-2 block text-sm text-primary">
                Skip rows with errors (continue importing valid rows)
              </label>
            </div>

            <button
              onClick={handleImport}
              disabled={importLoading || !selectedFile || !previewResult || selectedCount === 0}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {importLoading ? (
                <span className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Importing {selectedCount} items...
                </span>
              ) : (
                `📤 Import ${selectedCount > 0 ? `${selectedCount} ` : ''}Selected Items`
              )}
            </button>

            {/* Progress Bar */}
            {importLoading && (
              <div className="w-full">
                <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-1">
                  <span>Importing...</span>
                  <span>{importProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${importProgress}%` }}
                  ></div>
                </div>
              </div>
            )}

            {/* Import Results */}
            {importResult && (
              <div className={`mt-4 p-4 rounded-lg ${importResult.success
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
                }`}>
                <h3 className={`font-semibold mb-2 ${importResult.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                  {importResult.success ? '✅ Import Completed' : '❌ Import Failed'}
                </h3>
                <div className="text-sm space-y-1">
                  <div className={importResult.success ? 'text-green-700' : 'text-red-700'}>
                    Imported: {importResult.imported_count} assets
                  </div>
                  {importResult.skipped_count > 0 && (
                    <div className="text-yellow-700">
                      Skipped: {importResult.skipped_count} assets
                    </div>
                  )}
                  {importResult.errors && importResult.errors.length > 0 && (
                    <div className="mt-2">
                      <div className="font-medium text-red-700 mb-1">Errors:</div>
                      <ul className="list-disc list-inside space-y-1 text-red-600 max-h-40 overflow-y-auto">
                        {importResult.errors.map((error, index) => (
                          <li key={index} className="text-xs">{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="mt-8 card">
        <h2 className="text-xl font-bold text-primary mb-4">CSV Format Guide</h2>
        <div className="text-sm text-gray-500 dark:text-gray-400 space-y-2">
          <p>
            <strong>Required fields:</strong> asset_tag, serial_number, asset_type
          </p>
          <p>
            <strong>Optional fields:</strong> manufacturer, model, status, hostname, description, sku,
            purchase_cost, purchase_date, currency, supplier, po_number, datacenter_id, rack_id,
            rack_position_start, rack_position_end, container_id, height_u, power_consumption_watts,
            custom_fields (JSON string)
          </p>
          <p>
            <strong>Note:</strong> The asset_type must exist in your Asset Types before importing.
            Duplicate assets (same asset_tag and serial_number) will be skipped.
          </p>
          <p>
            <strong>Tip:</strong> Export your current assets first to see the exact format and field names.
            Rack and datacenter can be specified by name or code, and will be auto-detected if not specified.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CSVImportExport;
