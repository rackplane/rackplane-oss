// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface DatabaseSummary {
  backup_date?: string;
  version?: string;
  total_tables: number;
  total_records: number;
  tables: Array<{
    name: string;
    count: number;
  }>;
}

interface BackupValidation {
  valid: boolean;
  errors?: string[];
  summary?: DatabaseSummary;
}

interface ImportStats {
  started_at: string;
  completed_at?: string;
  tables_imported: number;
  total_records_imported: number;
  tables_cleared: number;
  errors: string[];
}

const Backup: React.FC = () => {
  const [summary, setSummary] = useState<DatabaseSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [clearExisting, setClearExisting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<BackupValidation | null>(null);
  const [importResult, setImportResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/v1/backup/summary`);
      setSummary(response.data);
    } catch (err: any) {
      logger.error('Error fetching summary:', err);
      setError(err.response?.data?.detail || 'Failed to fetch database summary');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/v1/backup/export`, {
        responseType: 'blob'
      });

      // Create download link
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const filename = `datacenter-backup-${timestamp}.json`;

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      alert(`Backup exported successfully as ${filename}`);
    } catch (err: any) {
      logger.error('Error exporting backup:', err);
      setError(err.response?.data?.detail || 'Failed to export database');
    } finally {
      setExporting(false);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setValidation(null);
    setImportResult(null);

    // Validate the file
    await validateFile(file);
  };

  const validateFile = async (file: File) => {
    setValidating(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_URL}/api/v1/backup/validate`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setValidation(response.data);
    } catch (err: any) {
      logger.error('Error validating file:', err);
      setError(err.response?.data?.detail || 'Failed to validate backup file');
      setValidation({ valid: false, errors: ['Failed to validate file'] });
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) {
      setError('Please select a backup file first');
      return;
    }

    if (!validation?.valid) {
      setError('Cannot import invalid backup file');
      return;
    }

    if (clearExisting) {
      const confirmed = window.confirm(
        '⚠️ WARNING: This will DELETE ALL existing data before importing!\n\n' +
        'Are you absolutely sure you want to proceed?\n\n' +
        'This action cannot be undone!'
      );
      if (!confirmed) return;

      const doubleConfirm = window.confirm(
        'Final confirmation: ALL EXISTING DATA WILL BE PERMANENTLY DELETED!\n\n' +
        'Type "DELETE" in the prompt to confirm.'
      );
      if (!doubleConfirm) return;
    }

    setImporting(true);
    setError(null);
    setImportResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post(
        `${API_URL}/api/v1/backup/import?clear_existing=${clearExisting}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setImportResult(response.data);

      if (response.data.success) {
        alert('✅ Database imported successfully!');
        await fetchSummary();
      } else {
        alert('⚠️ Import completed with errors. Check the details below.');
      }
    } catch (err: any) {
      logger.error('Error importing backup:', err);
      setError(err.response?.data?.detail || 'Failed to import database');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-primary">Database Backup & Restore</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Export and import your entire database for backup and recovery</p>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card mb-6" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
          <div className="flex items-start">
            <span className="text-2xl mr-3">❌</span>
            <div>
              <h3 className="font-bold" style={{ color: 'var(--danger)' }}>Error</h3>
              <p style={{ color: 'var(--danger)' }}>{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Current Database Summary */}
      <div className="card mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-primary">Current Database Status</h2>
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="btn-secondary text-sm"
          >
            {loading ? '⟳ Refreshing...' : '🔄 Refresh'}
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading database summary...</div>
        ) : summary ? (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(0, 123, 255, 0.1)' }}>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Tables</div>
                <div className="text-3xl font-bold" style={{ color: 'var(--primary)' }}>{summary.total_tables}</div>
              </div>
              <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Records</div>
                <div className="text-3xl font-bold" style={{ color: 'var(--success)' }}>{summary.total_records.toLocaleString()}</div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Table Name</th>
                    <th className="text-right">Record Count</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.tables.map((table) => (
                    <tr key={table.name}>
                      <td className="font-mono text-sm">{table.name}</td>
                      <td className="text-right font-semibold">{table.count.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">No summary available</div>
        )}
      </div>

      {/* Full Backup Section (Database + Files) */}
      <div className="card mb-6" style={{ background: 'linear-gradient(to right, rgba(147, 51, 234, 0.1), rgba(0, 123, 255, 0.1))', borderColor: 'rgba(147, 51, 234, 0.3)' }}>
        <h2 className="text-xl font-bold text-primary mb-4">📦 Full Backup (Database + Files)</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Download a complete backup archive (.tar.gz) containing both the database and all uploaded files
          (photos, documents, etc.). This is the recommended backup method for full system recovery.
        </p>
        <button
          onClick={async () => {
            setExporting(true);
            setError(null);
            try {
              const response = await axios.get(`${API_URL}/api/v1/backup/export-archive`, {
                responseType: 'blob'
              });

              const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
              const filename = `dcms_backup_${timestamp}.tar.gz`;

              const url = window.URL.createObjectURL(new Blob([response.data]));
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', filename);
              document.body.appendChild(link);
              link.click();
              link.remove();
              window.URL.revokeObjectURL(url);

              alert(`Full backup exported successfully as ${filename}`);
            } catch (err: any) {
              logger.error('Error exporting full backup:', err);
              setError(err.response?.data?.detail || 'Failed to export full backup archive');
            } finally {
              setExporting(false);
            }
          }}
          disabled={exporting}
          className="btn-primary"
        >
          {exporting ? '⟳ Exporting...' : '💾 Download Full Backup (.tar.gz)'}
        </button>
      </div>

      {/* Import Full Backup Archive Section */}
      <div className="card mb-6" style={{ background: 'linear-gradient(to right, rgba(147, 51, 234, 0.1), rgba(0, 123, 255, 0.1))', borderColor: 'rgba(147, 51, 234, 0.3)' }}>
        <h2 className="text-xl font-bold text-primary mb-4">📥 Import Full Backup Archive</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Restore from a full backup archive (.tar.gz) containing both database and files.
          This will restore everything including uploaded photos and documents.
        </p>

        <div className="mb-4">
          <label className="block text-sm font-medium text-primary mb-2">
            Select Full Backup Archive (.tar.gz)
          </label>
          <input
            type="file"
            accept=".tar.gz,.gz"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setSelectedFile(file);
              setError(null);
            }}
            className="input w-full"
            disabled={importing}
          />
        </div>

        <div className="mb-4 space-y-2">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={clearExisting}
              onChange={(e) => setClearExisting(e.target.checked)}
              disabled={importing}
              className="w-4 h-4 text-red-600 rounded focus:ring-2 focus:ring-red-500"
            />
            <span className="text-sm font-medium text-primary">
              ⚠️ Delete all existing data before importing (DANGEROUS!)
            </span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="skipFiles"
              onChange={(e) => {
                // Store skip_files state
                (window as any).skipFiles = e.target.checked;
              }}
              disabled={importing}
              className="w-4 h-4 text-gray-500 dark:text-gray-400 rounded focus:ring-2 focus:ring-gray-500"
            />
            <span className="text-sm font-medium text-primary">
              Skip restoring uploaded files (database only)
            </span>
          </label>
        </div>

        <button
          onClick={async () => {
            if (!selectedFile) {
              setError('Please select a backup archive file first');
              return;
            }

            if (clearExisting) {
              const confirmed = window.confirm(
                '⚠️ WARNING: This will DELETE ALL existing data before importing!\n\n' +
                'Are you absolutely sure you want to proceed?\n\n' +
                'This action cannot be undone!'
              );
              if (!confirmed) return;
            }

            setImporting(true);
            setError(null);
            setImportResult(null);

            try {
              const formData = new FormData();
              formData.append('file', selectedFile);

              const skipFiles = (window as any).skipFiles || false;

              const response = await axios.post(
                `${API_URL}/api/v1/backup/import-archive?clear_existing=${clearExisting}&skip_files=${skipFiles}`,
                formData,
                {
                  headers: {
                    'Content-Type': 'multipart/form-data'
                  }
                }
              );

              setImportResult(response.data);

              if (response.data.success) {
                alert('✅ Full backup imported successfully!');
                await fetchSummary();
              } else {
                alert('⚠️ Import completed with errors. Check the details below.');
              }
            } catch (err: any) {
              logger.error('Error importing full backup:', err);
              setError(err.response?.data?.detail || 'Failed to import full backup archive');
            } finally {
              setImporting(false);
            }
          }}
          disabled={!selectedFile || importing}
          className={`btn-primary ${!selectedFile || importing ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {importing ? '⟳ Importing...' : '📥 Import Full Backup Archive'}
        </button>
      </div>

      {/* Native Database Backup Section */}
      <div className="card mb-6" style={{ background: 'linear-gradient(to right, rgba(16, 185, 129, 0.1), rgba(0, 123, 255, 0.1))', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <h2 className="text-xl font-bold text-primary mb-4">🛡️ Native Database Backup (.dump)</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Download a native PostgreSQL dump file. This format is <strong>highly recommended</strong> for disaster recovery as it guarantees perfect data fidelity (including all sequences, IDs, and relationships).
        </p>
        <button
          onClick={async () => {
            setExporting(true);
            setError(null);
            try {
              const response = await axios.get(`${API_URL}/api/v1/backup/native/export`, {
                responseType: 'blob'
              });

              const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
              const filename = `dcms_native_${timestamp}.dump`;

              const url = window.URL.createObjectURL(new Blob([response.data]));
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', filename);
              document.body.appendChild(link);
              link.click();
              link.remove();
              window.URL.revokeObjectURL(url);

              alert(`Native database dump exported successfully as ${filename}`);
            } catch (err: any) {
              logger.error('Error exporting native backup:', err);
              setError(err.response?.data?.detail || 'Failed to export native database dump');
            } finally {
              setExporting(false);
            }
          }}
          disabled={exporting}
          className="btn-primary"
        >
          {exporting ? '⟳ Exporting...' : '💾 Download Native Database Dump (.dump)'}
        </button>
      </div>

      {/* Legacy JSON Export (Hidden or Demoted) */}
      <div className="card mb-6 opacity-75">
        <h2 className="text-xl font-bold text-gray-500 mb-4">📦 Legacy Database Export (JSON)</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Export database as a readable JSON file. Useful for partial data viewing or specific tenant migrations.
          <strong> Not recommended for full disaster recovery.</strong>
        </p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="btn-secondary"
        >
          {exporting ? '⟳ Exporting...' : '💾 Download JSON Export'}
        </button>
      </div>

      {/* Import Section (JSON Database Only) */}
      <div className="card">
        <h2 className="text-xl font-bold text-primary mb-4">📥 Import Database (JSON Only)</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Restore your database from a JSON backup file (database only, no files).
          You can either add data to the existing database or completely replace all existing data.
        </p>

        {/* File Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-primary mb-2">
            Select Backup File
          </label>
          <input
            type="file"
            accept=".json"
            onChange={handleFileSelect}
            className="input w-full"
            disabled={importing}
          />
        </div>

        {/* File Validation Result */}
        {validating && (
          <div className="border rounded p-4 mb-4" style={{ backgroundColor: 'rgba(0, 123, 255, 0.1)', borderColor: 'rgba(0, 123, 255, 0.3)' }}>
            <p style={{ color: 'var(--primary)' }}>🔍 Validating backup file...</p>
          </div>
        )}

        {validation && !validating && (
          <div
            className="border rounded p-4 mb-4"
            style={validation.valid
              ? { backgroundColor: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.3)' }
              : { backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }
            }
          >
            {validation.valid ? (
              <div>
                <h3 className="font-bold mb-2" style={{ color: 'var(--success)' }}>✅ Valid Backup File</h3>
                {validation.summary && (
                  <div className="text-sm text-primary">
                    <p><strong>Backup Date:</strong> {validation.summary.backup_date ? new Date(validation.summary.backup_date).toLocaleString() : 'Unknown'}</p>
                    <p><strong>Total Tables:</strong> {validation.summary.total_tables}</p>
                    <p><strong>Total Records:</strong> {validation.summary.total_records.toLocaleString()}</p>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <h3 className="font-bold mb-2" style={{ color: 'var(--danger)' }}>❌ Invalid Backup File</h3>
                {validation.errors && (
                  <ul className="list-disc list-inside text-sm" style={{ color: 'var(--danger)' }}>
                    {validation.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}

        {/* Import Options */}
        {validation?.valid && (
          <div className="mb-6">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={clearExisting}
                onChange={(e) => setClearExisting(e.target.checked)}
                disabled={importing}
                className="w-4 h-4 text-red-600 rounded focus:ring-2 focus:ring-red-500"
              />
              <span className="text-sm font-medium text-primary">
                ⚠️ Delete all existing data before importing (DANGEROUS!)
              </span>
            </label>
            {clearExisting && (
              <div className="mt-2 p-3 border rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                <p className="text-sm font-semibold" style={{ color: 'var(--danger)' }}>
                  ⚠️ WARNING: This will permanently delete ALL existing data in your database!
                </p>
              </div>
            )}
          </div>
        )}

        {/* Import Button */}
        <button
          onClick={handleImport}
          disabled={!validation?.valid || importing}
          className={`btn-primary ${!validation?.valid || importing ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {importing ? '⟳ Importing...' : '📥 Import Backup'}
        </button>

      </div>

      {/* Native Restore Section */}
      <div className="card mt-6" style={{ background: 'linear-gradient(to right, rgba(16, 185, 129, 0.1), rgba(0, 123, 255, 0.1))', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <h2 className="text-xl font-bold text-primary mb-4">🔄 Restore Native Database Dump</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          Restore from a native PostgreSQL dump (.dump).
          <br />
          <strong className="text-red-500">⚠️ WARNING: This will completely replace the current database!</strong>
        </p>

        <div className="mb-4">
          <input
            type="file"
            accept=".dump"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;

              const confirmed = window.confirm(
                '⚠️ CRITICAL WARNING: Native Restore is DESTRUCTIVE!\n\n' +
                'This will DROP the current database and replace it entirely with the backup.\n' +
                'All current data will be LOST.\n\n' +
                'Do you want to proceed?'
              );

              if (!confirmed) {
                e.target.value = '';
                return;
              }

              setImporting(true);
              setError(null);

              try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await axios.post(`${API_URL}/api/v1/backup/native/import`, formData, {
                  headers: { 'Content-Type': 'multipart/form-data' }
                });

                if (response.data.success) {
                  alert('✅ Database restored successfully! The page will now reload.');
                  window.location.reload();
                }
              } catch (err: any) {
                logger.error('Error importing native backup:', err);
                setError(err.response?.data?.detail || 'Failed to restore native backup');
              } finally {
                setImporting(false);
                e.target.value = ''; // Reset input
              }
            }}
            className="input w-full"
            disabled={importing}
          />
        </div>

        {/* Import Result */}
        {importResult && (
          <div
            className="mt-6 border rounded p-4"
            style={importResult.success
              ? { backgroundColor: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.3)' }
              : { backgroundColor: 'rgba(245, 158, 11, 0.1)', borderColor: 'rgba(245, 158, 11, 0.3)' }
            }
          >
            <h3
              className="font-bold mb-2"
              style={{ color: importResult.success ? 'var(--success)' : 'var(--warning)' }}
            >
              {importResult.success ? '✅ Import Successful' : '⚠️ Import Completed with Warnings'}
            </h3>
            <p className="text-sm text-primary mb-2">{importResult.message}</p>
            {importResult.stats && (
              <div className="text-sm text-primary space-y-1">
                <p><strong>Tables Imported:</strong> {importResult.stats.tables_imported}</p>
                <p><strong>Total Records:</strong> {importResult.stats.total_records_imported.toLocaleString()}</p>
                {importResult.stats.tables_cleared > 0 && (
                  <p><strong>Tables Cleared:</strong> {importResult.stats.tables_cleared}</p>
                )}
                {importResult.stats.errors.length > 0 && (
                  <div className="mt-3">
                    <p className="font-bold" style={{ color: 'var(--danger)' }}>Errors:</p>
                    <ul className="list-disc list-inside text-xs" style={{ color: 'var(--danger)' }}>
                      {importResult.stats.errors.map((err: string, idx: number) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Best Practices */}
      <div className="card mt-6" style={{ backgroundColor: 'rgba(0, 123, 255, 0.1)', borderColor: 'rgba(0, 123, 255, 0.3)' }}>
        <h3 className="font-bold mb-2" style={{ color: 'var(--primary)' }}>💡 Best Practices</h3>
        <ul className="list-disc list-inside text-sm space-y-1" style={{ color: 'var(--primary)' }}>
          <li>Create regular backups (daily or weekly recommended)</li>
          <li>Store backups in multiple locations (local + cloud storage)</li>
          <li>Test your backups periodically by importing to a test environment</li>
          <li>Label backup files with dates for easy identification</li>
          <li>Keep at least 3-5 recent backups for redundancy</li>
          <li>Never use "Clear existing data" on production without testing first</li>
        </ul>
      </div>
    </div>
  );
};

export default Backup;
