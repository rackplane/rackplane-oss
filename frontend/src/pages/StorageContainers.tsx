// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import LabelPrintModal from '../components/LabelPrintModal';

// Helper function to format API errors
const formatError = (error: any): string => {
  if (typeof error === 'string') return error;
  if (Array.isArray(error)) {
    return error.map(err => {
      const field = err.loc ? err.loc.join('.') : 'unknown';
      return `${field}: ${err.msg}`;
    }).join('; ');
  }
  if (typeof error === 'object' && error.msg) return error.msg;
  return 'An error occurred';
};

interface AssetTypeInfo {
  asset_type: string;
  display_name: string;
  count: number;
}

interface StorageContainer {
  id: number;
  name: string;
  original_name?: string; // Original model name for asset-based boxes
  asset_tag?: string; // Asset tag for tracking (asset-based boxes)
  container_type: string;
  datacenter_id?: number;
  room_id?: number;
  location?: string;
  description?: string;
  barcode?: string;
  created_at: string;
  updated_at: string;
  asset_types?: AssetTypeInfo[];
  total_assets?: number;
  is_storage_box?: boolean;
}

interface StorageContainerFormData {
  name: string;
  container_type: string;
  datacenter_id: string;
  room_id: string;
  location: string;
  description: string;
  barcode: string;
}

interface Datacenter {
  id: number;
  name: string;
  code: string;
}

interface Room {
  id: number;
  name: string;
  datacenter_id: number;
}

/**
 * Helper function to determine if a storage container is empty.
 * Prefers total_assets when it's a number, falls back to asset_types otherwise.
 * This centralizes the empty-check logic to avoid drift between handleDelete,
 * the filter, and the delete button styling.
 */
const isContainerEmpty = (container: StorageContainer | undefined): boolean => {
  if (!container) return true;
  // Prefer total_assets when it's a number
  if (typeof container.total_assets === 'number') {
    return container.total_assets === 0;
  }
  // Fall back to asset_types check
  if (!container.asset_types) return true;
  return container.asset_types.length === 0;
};

const StorageContainers: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { t } = useWhiteLabel();
  const [searchParams] = useSearchParams();
  const [containers, setContainers] = useState<StorageContainer[]>([]);
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterDatacenter, setFilterDatacenter] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingContainer, setEditingContainer] = useState<StorageContainer | null>(null);
  const [formData, setFormData] = useState<StorageContainerFormData>({
    name: '',
    container_type: 'box',
    datacenter_id: '',
    room_id: '',
    location: '',
    description: '',
    barcode: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<keyof StorageContainer | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [showLabelPrint, setShowLabelPrint] = useState(false);
  const [printingContainer, setPrintingContainer] = useState<StorageContainer | null>(null);
  const [filterEmpty, setFilterEmpty] = useState(false);

  useEffect(() => {
    // Read datacenter filter from URL params
    const datacenterIdParam = searchParams.get('datacenter_id');
    if (datacenterIdParam) {
      const dcId = parseInt(datacenterIdParam);
      if (!isNaN(dcId)) {
        setFilterDatacenter(dcId);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    fetchContainers();
    fetchDatacenters();
    fetchRooms();
  }, []);

  const fetchContainers = async () => {
    try {
      // Fetch StorageContainer records only (Asset-based storage boxes have been migrated)
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/`);
      const storageContainers = response.data || [];
      logger.debug(`Fetched ${storageContainers.length} storage containers`, storageContainers);
      setContainers(storageContainers);
    } catch (err: any) {
      logger.error('Failed to fetch storage containers:', err);
      setError(`Failed to load ${t('storage').toLowerCase()} ${t('containers').toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchDatacenters = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
    } catch (error) {
      logger.error('Error fetching datacenters:', error);
    }
  };

  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/rooms`);
      setRooms(response.data || []);
    } catch (error) {
      logger.error('Error fetching rooms:', error);
    }
  };

  const openAddModal = () => {
    setEditingContainer(null);
    setFormData({
      name: '',
      container_type: 'box',
      datacenter_id: '',
      room_id: '',
      location: '',
      description: '',
      barcode: '',
    });
    setError(null);
    setShowModal(true);
  };

  const openEditModal = (container: StorageContainer) => {
    setEditingContainer(container);
    setFormData({
      name: container.name,
      container_type: container.container_type,
      datacenter_id: container.datacenter_id?.toString() || '',
      room_id: container.room_id?.toString() || '',
      location: container.location || '',
      description: container.description || '',
      barcode: container.barcode || '',
    });
    setError(null);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingContainer(null);
    setError(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (editingContainer) {
        // Update StorageContainer record
        const payload = {
          name: formData.name,
          container_type: formData.container_type,
          datacenter_id: formData.datacenter_id ? parseInt(formData.datacenter_id) : null,
          room_id: formData.room_id ? parseInt(formData.room_id) : null,
          location: formData.location || null,
          description: formData.description || null,
          barcode: formData.barcode || null,
        };
        await axios.put(`${API_URL}/api/v1/storage-containers/${editingContainer.id}`, payload);
      } else {
        // Create new StorageContainer
        const payload = {
          name: formData.name,
          container_type: formData.container_type,
          datacenter_id: formData.datacenter_id ? parseInt(formData.datacenter_id) : null,
          room_id: formData.room_id ? parseInt(formData.room_id) : null,
          location: formData.location || null,
          description: formData.description || null,
          barcode: formData.barcode || null,
        };
        await axios.post(`${API_URL}/api/v1/storage-containers/`, payload);
      }

      await fetchContainers();
      closeModal();
    } catch (err: any) {
      logger.error('Error saving storage container:', err);
      const errorDetail = err.response?.data?.detail || `Failed to save ${t('storage').toLowerCase()} ${t('container').toLowerCase()}`;
      setError(formatError(errorDetail));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    const container = containers.find(c => c.id === id);
    const isEmpty = isContainerEmpty(container);

    let confirmMessage = `Are you sure you want to delete this ${t('storage').toLowerCase()} ${t('container').toLowerCase()}?`;
    if (!isEmpty) {
      const itemCount = container?.total_assets || container?.asset_types?.reduce((sum, at) => sum + at.count, 0) || 0;
      confirmMessage = `⚠️ WARNING: This container has ${itemCount} item(s) in it. Deleting it will remove the container but the items will remain unassigned. Are you sure you want to delete?`;
    }

    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/storage-containers/${id}`);
      await fetchContainers();
    } catch (err: any) {
      logger.error('Error deleting storage container:', err);
      alert(`Failed to delete ${t('container').toLowerCase()}: ` + (err.response?.data?.detail || err.message));
    }
  };

  const handleSort = (column: keyof StorageContainer) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const getSortIndicator = (column: keyof StorageContainer) => {
    if (sortColumn !== column) return ' ↕';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  const filteredContainers = containers.filter(container => {
    // Filter by datacenter if selected
    if (filterDatacenter) {
      if (container.datacenter_id !== filterDatacenter) {
        return false;
      }
    }

    // Filter by empty status
    if (filterEmpty) {
      if (!isContainerEmpty(container)) {
        return false;
      }
    }

    // Filter by search
    return (
      container.name.toLowerCase().includes(search.toLowerCase()) ||
      container.container_type.toLowerCase().includes(search.toLowerCase()) ||
      container.location?.toLowerCase().includes(search.toLowerCase()) ||
      container.barcode?.toLowerCase().includes(search.toLowerCase())
    );
  });

  const sortedContainers = [...filteredContainers].sort((a, b) => {
    if (!sortColumn) return 0;

    const aValue = a[sortColumn];
    const bValue = b[sortColumn];

    if (aValue === undefined || aValue === null) return 1;
    if (bValue === undefined || bValue === null) return -1;

    const comparison = aValue > bValue ? 1 : -1;
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  // Helper function to get datacenter name
  const getDatacenterName = (datacenterId?: number) => {
    if (!datacenterId) return '-';
    const dc = datacenters.find(d => d.id === datacenterId);
    return dc ? `${dc.name} (${dc.code})` : '-';
  };

  // Helper function to get room name
  const getRoomName = (roomId?: number) => {
    if (!roomId) return '-';
    const room = rooms.find(r => r.id === roomId);
    return room ? room.name : '-';
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('storage')} {t('containers')}</h1>
        {isAuthenticated && (
          <button onClick={openAddModal} className="btn-primary">
            + Add {t('container')}
          </button>
        )}
        {!isAuthenticated && (
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">Login to make changes</p>
        )}
      </div>

      {/* Search and Filter */}
      <div className="card mb-6">
        <div className="flex gap-4 items-center">
          <input
            type="text"
            placeholder={`Search ${t('containers').toLowerCase()}...`}
            className="input flex-1"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-primary whitespace-nowrap">
              Filter by {t('location')}:
            </label>
            <select
              value={filterDatacenter || ''}
              onChange={(e) => {
                const dcId = e.target.value ? parseInt(e.target.value) : null;
                setFilterDatacenter(dcId);
                // Update URL params
                const params = new URLSearchParams(searchParams);
                if (dcId) {
                  params.set('datacenter_id', dcId.toString());
                } else {
                  params.delete('datacenter_id');
                }
                window.history.replaceState({}, '', `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`);
              }}
              className="input"
            >
              <option value="">All {t('locations')}</option>
              {datacenters.map(dc => (
                <option key={dc.id} value={dc.id}>
                  {dc.name} ({dc.code})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filterEmpty}
                onChange={(e) => setFilterEmpty(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-primary whitespace-nowrap">
                Show only empty
              </span>
            </label>
          </div>
        </div>
        {(filterDatacenter || filterEmpty) && (
          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {filterDatacenter && `Showing ${t('storage').toLowerCase()} ${t('containers').toLowerCase()} in ${getDatacenterName(filterDatacenter)}`}
            {filterDatacenter && filterEmpty && ' • '}
            {filterEmpty && 'Showing only empty containers'}
          </div>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-500 dark:text-gray-400">Loading {t('storage').toLowerCase()} {t('containers').toLowerCase()}...</div>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th
                  className="cursor-pointer hover:bg-table-row-hover select-none"
                  onClick={() => handleSort('name')}
                >
                  Name{getSortIndicator('name')}
                </th>
                <th
                  className="cursor-pointer hover:bg-table-row-hover select-none"
                  onClick={() => handleSort('container_type')}
                >
                  Type{getSortIndicator('container_type')}
                </th>
                <th>{t('location')}</th>
                <th>Room</th>
                <th>{t('item')} {t('categories')}</th>
                <th>Additional Location</th>
                <th
                  className="cursor-pointer hover:bg-table-row-hover select-none"
                  onClick={() => handleSort('barcode')}
                >
                  Barcode{getSortIndicator('barcode')}
                </th>
                <th className="hide-lg">Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedContainers.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No {t('storage').toLowerCase()} {t('containers').toLowerCase()} found
                  </td>
                </tr>
              ) : (
                sortedContainers.map((container) => (
                  <tr key={container.id}>
                    <td className="font-medium">
                      <Link
                        to={`/storage-containers/${container.id}`}
                        className="text-primary hover:text-primary-hover dark:text-accent dark:hover:text-accent/80 hover:underline"
                      >
                        {container.name}
                      </Link>
                    </td>
                    <td className="capitalize">{container.container_type}</td>
                    <td>{getDatacenterName(container.datacenter_id)}</td>
                    <td>{getRoomName(container.room_id)}</td>
                    <td>
                      {container.asset_types && container.asset_types.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {container.asset_types.map((assetType, idx) => (
                            <span key={idx} className="badge badge-info text-xs">
                              {assetType.display_name} ({assetType.count})
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="badge badge-warning text-xs font-semibold">Empty</span>
                      )}
                    </td>
                    <td>{container.location || '-'}</td>
                    <td><code className="text-sm">{container.barcode || '-'}</code></td>
                    <td className="hide-lg max-w-xs truncate">{container.description || '-'}</td>
                    <td>
                      <div className="table-actions">
                        <button
                          onClick={() => {
                            setPrintingContainer(container);
                            setShowLabelPrint(true);
                          }}
                          className="text-purple-600 hover:text-purple-800"
                          title="Print label"
                        >
                          🏷️
                        </button>
                        {isAuthenticated && (
                          <>
                            <button
                              onClick={() => openEditModal(container)}
                              className="text-green-600 hover:text-green-800"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(container.id)}
                              className={`${isContainerEmpty(container)
                                ? 'text-red-600 hover:text-red-800 font-semibold'
                                : 'text-red-500 hover:text-red-700 opacity-75'
                                }`}
                              title={
                                isContainerEmpty(container)
                                  ? 'Delete empty container'
                                  : 'Warning: Container has items'
                              }
                            >
                              Del
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {sortedContainers.length > 0 && (
            <div className="px-6 py-4 border-t border-gray-200">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Showing {sortedContainers.length} of {containers.length} {t('containers').toLowerCase()}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4 p-6">
            <h2 className="text-2xl font-bold dark:text-gray-100 mb-6">
              {editingContainer
                ? `Edit ${t('storage')} {t('container')}`
                : `Add ${t('storage')} {t('container')}`}
            </h2>

            {editingContainer?.is_storage_box && (
              <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200 px-4 py-3 rounded mb-4 text-sm">
                <p className="font-semibold">{t('container')} Information:</p>
                <p>{t('item')} Tag: <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">{editingContainer.asset_tag}</code></p>
                <p>Serial Number: <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">{editingContainer.barcode}</code></p>
                <p className="mt-2 text-xs">These identifiers are used for tracking and cannot be changed.</p>
              </div>
            )}

            {error && (
              <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Name *
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="input w-full"
                    placeholder="e.g., Box 001, Shelf A, Cabinet 3"
                  />
                </div>

                {/* Container Type */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('container')} Type *
                  </label>
                  <select
                    name="container_type"
                    value={formData.container_type}
                    onChange={handleInputChange}
                    required
                    className="input w-full"
                  >
                    <option value="box">Box</option>
                    <option value="bin">Bin</option>
                    <option value="shelf">Shelf</option>
                    <option value="cabinet">Cabinet</option>
                    <option value="drawer">Drawer</option>
                    <option value="rack">{t('bin')}</option>
                    <option value="pallet">Pallet</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                {/* Datacenter */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('location')}
                  </label>
                  <select
                    name="datacenter_id"
                    value={formData.datacenter_id}
                    onChange={handleInputChange}
                    className="input w-full"
                  >
                    <option value="">-- Select {t('location')} --</option>
                    {datacenters.map(dc => (
                      <option key={dc.id} value={dc.id}>
                        {dc.name} ({dc.code})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Optional - Select {t('location').toLowerCase()} where this {t('container').toLowerCase()} is located
                  </p>
                </div>

                {/* Room */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Room
                  </label>
                  <select
                    name="room_id"
                    value={formData.room_id}
                    onChange={handleInputChange}
                    className="input w-full"
                    disabled={!formData.datacenter_id}
                  >
                    <option value="">-- Select Room --</option>
                    {rooms
                      .filter(room => !formData.datacenter_id || room.datacenter_id === parseInt(formData.datacenter_id))
                      .map(room => (
                        <option key={room.id} value={room.id}>
                          {room.name}
                        </option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {!formData.datacenter_id ? `Select a ${t('location').toLowerCase()} first` : 'Optional - Select specific room'}
                  </p>
                </div>

                {/* Additional Location */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Additional Location Info
                  </label>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="e.g., Aisle 3, Bay 5, Top Shelf"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Optional - Specific location details within the room
                  </p>
                </div>

                {/* Barcode */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Barcode
                  </label>
                  <input
                    type="text"
                    name="barcode"
                    value={formData.barcode}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="Scan or enter barcode"
                  />
                </div>

                {/* Description */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-primary mb-2">
                    Description
                  </label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleInputChange}
                    className="input w-full"
                    rows={3}
                    placeholder={`Additional notes about this ${t('container').toLowerCase()}...`}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="btn-secondary"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : editingContainer ? `Update ${t('container')}` : `Create ${t('container')}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Label Print Modal */}
      {printingContainer && (
        <LabelPrintModal
          isOpen={showLabelPrint}
          onClose={() => {
            setShowLabelPrint(false);
            setPrintingContainer(null);
          }}
          item={printingContainer}
          itemType="container"
        />
      )}
    </div>
  );
};

export default StorageContainers;
