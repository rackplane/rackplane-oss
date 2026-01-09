import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import {
  DeviceTypeSummary,
  DeviceTypeImportResponse,
  VendorSKUSummary
} from '../types/devicetype';

interface DeviceTypeImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (sku: VendorSKUSummary) => void;
}

const DeviceTypeImportModal: React.FC<DeviceTypeImportModalProps> = ({ isOpen, onClose, onImport }) => {
  const [manufacturers, setManufacturers] = useState<string[]>([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState<string | null>(null);
  const [devices, setDevices] = useState<DeviceTypeSummary[]>([]);
  const [filteredDevices, setFilteredDevices] = useState<DeviceTypeSummary[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const [importingDevices, setImportingDevices] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Reset state when modal is closed to prevent stale data on reopen
  const resetState = () => {
    setSelectedManufacturer(null);
    setDevices([]);
    setFilteredDevices([]);
    setSearchTerm('');
    setError(null);
    setSuccessMessage(null);
    setImportingDevices(new Set());
  };

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      resetState();
    }
  }, [isOpen]);

  // Load manufacturers on mount
  useEffect(() => {
    if (isOpen) {
      loadManufacturers();
    }
  }, [isOpen]);

  // Load devices when manufacturer is selected
  useEffect(() => {
    if (selectedManufacturer) {
      loadDevices(selectedManufacturer);
    } else {
      setDevices([]);
      setFilteredDevices([]);
    }
  }, [selectedManufacturer]);

  // Filter devices based on search term
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredDevices(devices);
    } else {
      const searchLower = searchTerm.toLowerCase();
      const filtered = devices.filter(
        (device) =>
          device.slug.toLowerCase().includes(searchLower) ||
          device.name.toLowerCase().includes(searchLower)
      );
      setFilteredDevices(filtered);
    }
  }, [searchTerm, devices]);

  const loadManufacturers = async () => {
    setLoading(true);
    setError(null);

    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
      const response = await axios.get(`${API_URL}/api/v1/netbox-devicetypes/manufacturers`, {
        headers
      });

      setManufacturers(response.data.manufacturers);
    } catch (err: any) {
      logger.error('Error loading manufacturers:', err);
      setError(err.response?.data?.detail || 'Failed to load manufacturers.');
    } finally {
      setLoading(false);
    }
  };

  const loadDevices = async (manufacturer: string) => {
    setDevicesLoading(true);
    setError(null);
    setSearchTerm(''); // Reset search when changing manufacturer

    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
      const response = await axios.get(
        `${API_URL}/api/v1/netbox-devicetypes/manufacturers/${encodeURIComponent(manufacturer)}/devices`,
        { headers }
      );

      setDevices(response.data.devices);
      setFilteredDevices(response.data.devices);
    } catch (err: any) {
      logger.error('Error loading devices:', err);
      setError(err.response?.data?.detail || 'Failed to load device types.');
      setDevices([]);
      setFilteredDevices([]);
    } finally {
      setDevicesLoading(false);
    }
  };

  const handleImport = async (device: DeviceTypeSummary) => {
    if (!selectedManufacturer) return;

    // Track this specific device as importing
    setImportingDevices(prev => new Set(prev).add(device.slug));
    setError(null);
    setSuccessMessage(null);

    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
      const response = await axios.post<DeviceTypeImportResponse>(
        `${API_URL}/api/v1/netbox-devicetypes/import`,
        {
          manufacturer: selectedManufacturer,
          slug: device.slug
        },
        { headers }
      );

      if (response.data.success && response.data.sku) {
        setSuccessMessage(response.data.message);
        onImport(response.data.sku);

        // Close modal after a short delay
        setTimeout(() => {
          onClose();
          setSuccessMessage(null);
        }, 1500);
      }
    } catch (err: any) {
      logger.error('Error importing device type:', err);

      // Handle specific error cases
      if (err.response?.status === 409) {
        setError('This device type has already been imported.');
      } else if (err.response?.status === 429) {
        setError('GitHub API rate limit exceeded. Please try again later.');
      } else {
        setError(err.response?.data?.detail || 'Failed to import device type.');
      }
    } finally {
      // Remove this device from importing state
      setImportingDevices(prev => {
        const next = new Set(prev);
        next.delete(device.slug);
        return next;
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-primary">Import NetBox Device Type</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Browse and import device specifications from the NetBox Community library
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-hidden flex gap-6">
          {/* Left Column - Manufacturers */}
          <div className="w-1/3 flex flex-col border-r border-gray-200 dark:border-gray-700 pr-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Manufacturers</h3>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : manufacturers.length === 0 ? (
              <div className="flex-1 flex items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
                No manufacturers available.
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-1">
                {manufacturers.map((mfr) => (
                  <button
                    key={mfr}
                    onClick={() => setSelectedManufacturer(mfr)}
                    className={`w-full text-left px-3 py-2 rounded-md transition-colors ${selectedManufacturer === mfr
                      ? 'bg-primary text-white'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-white'
                      }`}
                  >
                    {mfr}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right Column - Device Types */}
          <div className="flex-1 flex flex-col">
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">
                {selectedManufacturer ? `${selectedManufacturer} Device Types` : 'Select a Manufacturer'}
              </h3>

              {selectedManufacturer && (
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search device types..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              )}
            </div>

            {/* Error/Success Messages */}
            {error && (
              <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-400 rounded">
                {error}
              </div>
            )}

            {successMessage && (
              <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-400 rounded">
                {successMessage}
              </div>
            )}

            {/* Device List */}
            <div className="flex-1 overflow-y-auto">
              {!selectedManufacturer ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  Select a manufacturer to view device types
                </div>
              ) : devicesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : filteredDevices.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  {searchTerm ? 'No device types match your search' : 'No device types found'}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredDevices.map((device) => (
                    <div
                      key={device.slug}
                      className="p-3 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 flex justify-between items-center"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {device.name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {device.slug}
                        </div>
                      </div>

                      <button
                        onClick={() => handleImport(device)}
                        disabled={importingDevices.has(device.slug)}
                        className="ml-4 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed text-sm whitespace-nowrap"
                      >
                        {importingDevices.has(device.slug) ? 'Importing...' : 'Import'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Results count */}
            {selectedManufacturer && filteredDevices.length > 0 && (
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                Showing {filteredDevices.length} of {devices.length} device types
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DeviceTypeImportModal;
