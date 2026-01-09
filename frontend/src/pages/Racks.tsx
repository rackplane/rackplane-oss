// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { RackView } from '../components/RackView';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import logger from '../utils/logger';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  rack_id?: number;
  rack_position_start?: number;
  rack_position_end?: number;
  height_u?: number;
  status?: string;
  asset_type?: string;
  power_consumption_watts?: number;
}

interface Rack {
  id: number;
  name: string;
  code: string;
  height_u: number;
  datacenter_id: number;
  room_id?: number;
  power_capacity_watts?: number;
  row?: string;
  position?: string;
}

interface Datacenter {
  id: number;
  name: string;
  code: string;
}

interface Room {
  id: number;
  name: string;
  code: string;
  datacenter_id: number;
}

interface StorageContainer {
  id: number;
  name: string;
  container_type: string;
  location?: string;
  room_id?: number;
  datacenter_id?: number;
  total_assets: number;
}

interface ContainerAsset {
  id: number;
  asset_tag: string;
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  description?: string;
  asset_type?: string;
  custom_fields?: {
    quantity?: number;
    [key: string]: any;
  };
}

const Racks: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { t } = useWhiteLabel();
  const [racks, setRacks] = useState<Rack[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [storageContainers, setStorageContainers] = useState<StorageContainer[]>([]);
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDatacenter, setFilterDatacenter] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  // Storage containers modal state
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [selectedRackForStorage, setSelectedRackForStorage] = useState<Rack | null>(null);
  const [modalContainers, setModalContainers] = useState<StorageContainer[]>([]);
  const [modalRoom, setModalRoom] = useState<Room | null>(null);
  const [expandedContainers, setExpandedContainers] = useState<Set<number>>(new Set());
  const [containerItems, setContainerItems] = useState<Map<number, ContainerAsset[]>>(new Map());
  const [loadingItems, setLoadingItems] = useState<Set<number>>(new Set());
  const [expandedDescriptions, setExpandedDescriptions] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (filterDatacenter) {
      fetchRacks(filterDatacenter);
    } else {
      fetchAllRacks();
    }
  }, [filterDatacenter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchAllRacks(),
        fetchAssets(),
        fetchStorageContainers(),
        fetchDatacenters(),
        fetchRooms()
      ]);
    } catch (error) {
      logger.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllRacks = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`);
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching racks:', error);
      setRacks([]);
    }
  };

  const fetchRacks = async (datacenterId: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`, {
        params: { datacenter_id: datacenterId }
      });
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching racks:', error);
      setRacks([]);
    }
  };

  const fetchAssets = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/assets/`, {
        params: { limit: 1000 }
      });
      setAssets(response.data.assets || []);
    } catch (error) {
      logger.error('Error fetching assets:', error);
      setAssets([]);
    }
  };

  const fetchDatacenters = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
    } catch (error) {
      logger.error('Error fetching datacenters:', error);
      setDatacenters([]);
    }
  };

  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/rooms`);
      setRooms(response.data || []);
    } catch (error) {
      logger.error('Error fetching rooms:', error);
      setRooms([]);
    }
  };

  const fetchStorageContainers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/`, {
        params: { limit: 1000 }
      });
      setStorageContainers(response.data || []);
    } catch (error) {
      logger.error('Error fetching storage containers:', error);
      setStorageContainers([]);
    }
  };

  const getRackAssets = (rackId: number): Asset[] => {
    // Only return assets that are actually mounted (have rack_position_start)
    return assets.filter(asset =>
      asset.rack_id === rackId &&
      asset.rack_position_start &&
      asset.rack_position_start >= 1
    );
  };

  // Helper function to get containers for a rack (returns actual container objects)
  const getContainersForRack = (rack: Rack): StorageContainer[] => {
    // Extract numeric identifier from rack code (e.g., "8-31" from "RACK-8-31")
    // Normalize to handle both dots and dashes
    const extractRackNumber = (code: string): string => {
      // Remove "RACK-" prefix if present, then normalize dots/dashes
      const normalized = code.toLowerCase().replace(/^rack-?/, '').trim();
      // Replace dots with dashes for consistent matching
      return normalized.replace(/\./g, '-');
    };

    const rackNumber = extractRackNumber(rack.code);

    // Filter containers that match this rack:
    // Priority: 1) Same datacenter, 2) Same room, 3) Container mentions this specific rack, 4) All containers (for demo)
    return storageContainers.filter(container => {
      // If datacenter filter is active, only show containers in that datacenter
      if (filterDatacenter) {
        // Check container's datacenter_id directly
        if (container.datacenter_id && container.datacenter_id !== filterDatacenter) {
          return false;
        }
        // If container doesn't have datacenter_id, check via room
        if (!container.datacenter_id && container.room_id) {
          const room = rooms.find(r => r.id === container.room_id);
          if (!room || room.datacenter_id !== filterDatacenter) {
            return false;
          }
        }
        // If container has neither datacenter_id nor room_id, exclude it when filter is active
        if (!container.datacenter_id && !container.room_id) {
          return false;
        }
      }

      // If container mentions a specific rack in location/name, it must match this rack
      const locationText = (container.location || '').toLowerCase();
      const nameText = (container.name || '').toLowerCase();
      const normalizedLocation = locationText.replace(/\./g, '-');
      const normalizedName = nameText.replace(/\./g, '-');
      const mentionsRack = locationText.includes('rack') || nameText.includes('rack');

      if (mentionsRack) {
        const matchesThisRack = normalizedLocation.includes(rackNumber) || normalizedName.includes(rackNumber);
        if (!matchesThisRack) return false;
        // If it explicitly mentions this rack, treat it as nearby
        return true;
      }

      // Match by room – storage is considered "nearby" when it's in the same room/cage
      if (container.room_id && rack.room_id && container.room_id === rack.room_id) {
        return true;
      }

      // If container is in a specific room, it should only match racks in that same room
      // Don't fall back to datacenter-level matching for containers in rooms
      if (container.room_id && !rack.room_id) {
        return false;
      }

      // Only fall back to datacenter-level matching when BOTH rack and container have no room
      // This prevents racks from matching containers in different rooms/datacenters
      if (!rack.room_id && !container.room_id && container.datacenter_id && rack.datacenter_id && container.datacenter_id === rack.datacenter_id) {
        return true;
      }

      // Otherwise, not considered nearby to this rack
      return false;
    });
  };

  const getRackStorageInfo = (rack: Rack): { containers: number; items: number } => {
    const containersForRack = getContainersForRack(rack);
    const totalItems = containersForRack.reduce((sum, container) => sum + container.total_assets, 0);

    return {
      containers: containersForRack.length,
      items: totalItems
    };
  };

  // Calculate power usage for a rack
  // Note: power_consumption_watts might be PSU size, not actual usage
  // We use 70% of PSU size as a conservative estimate of typical load
  const getRackPowerInfo = (rack: Rack): { used: number; total: number; percentage: number } => {
    const rackAssets = getRackAssets(rack.id);
    // Use 70% of PSU size as estimated actual power draw (typical server load)
    const estimatedUsedPower = rackAssets.reduce((sum, asset) => {
      const psuSize = asset.power_consumption_watts || 0;
      // Assume 70% typical load (conservative estimate)
      return sum + (psuSize * 0.7);
    }, 0);
    const totalPower = rack.power_capacity_watts || 0;
    const percentage = totalPower > 0 ? Math.round((estimatedUsedPower / totalPower) * 100) : 0;

    return {
      used: estimatedUsedPower / 1000, // Convert to kW
      total: totalPower / 1000, // Convert to kW
      percentage
    };
  };

  const getDatacenterName = (datacenterId: number): string => {
    const dc = datacenters.find(d => d.id === datacenterId);
    return dc ? dc.name : 'Unknown';
  };

  const getRoomName = (roomId?: number): string => {
    if (!roomId) return '-';
    const room = rooms.find(r => r.id === roomId);
    return room ? room.name : 'Unknown';
  };

  // Open storage containers modal for a rack
  const openStorageModal = async (rack: Rack) => {
    setSelectedRackForStorage(rack);
    setShowStorageModal(true);
    setExpandedContainers(new Set());
    setContainerItems(new Map());

    // Fetch room details if rack has a room
    if (rack.room_id) {
      try {
        const response = await axios.get(`${API_URL}/api/v1/locations/rooms/${rack.room_id}`);
        setModalRoom(response.data);
      } catch (err: any) {
        logger.error('Failed to load room details:', err);
        setModalRoom(null);
      }
    } else {
      setModalRoom(null);
    }

    // Use the same logic as getRackStorageInfo to determine relevant containers
    const relevantContainers = getContainersForRack(rack);
    setModalContainers(relevantContainers);
  };

  // Fetch container items when expanded (for modal)
  const fetchModalContainerItems = async (containerId: number) => {
    if (containerItems.has(containerId)) {
      return;
    }

    setLoadingItems((prev: Set<number>) => new Set(prev).add(containerId));
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/${containerId}/assets`);
      setContainerItems((prev: Map<number, ContainerAsset[]>) => {
        const newMap = new Map(prev);
        newMap.set(containerId, response.data);
        return newMap;
      });
    } catch (err: any) {
      logger.error('Failed to load container items:', err);
      setContainerItems((prev: Map<number, ContainerAsset[]>) => {
        const newMap = new Map(prev);
        newMap.set(containerId, []);
        return newMap;
      });
    } finally {
      setLoadingItems((prev: Set<number>) => {
        const newSet = new Set(prev);
        newSet.delete(containerId);
        return newSet;
      });
    }
  };

  // Toggle container expansion (for modal)
  const toggleModalContainerExpansion = (containerId: number) => {
    setExpandedContainers((prev: Set<number>) => {
      const newSet = new Set(prev);
      if (newSet.has(containerId)) {
        newSet.delete(containerId);
      } else {
        newSet.add(containerId);
        fetchModalContainerItems(containerId);
      }
      return newSet;
    });
  };

  // Helper functions for modal
  const getModalContainerRackInfo = (container: StorageContainer): { rackCode: string | null; isCurrentRack: boolean } => {
    if (!selectedRackForStorage) return { rackCode: null, isCurrentRack: false };

    const extractRackNumber = (code: string): string => {
      const normalized = code.toLowerCase();
      if (normalized.includes('rack-')) {
        return normalized.split('rack-')[1].replace(/\./g, '-');
      } else if (normalized.includes('rack')) {
        return normalized.split('rack')[1].replace(/\./g, '-').replace(/^-+/, '');
      }
      return normalized.replace(/\./g, '-');
    };

    const currentRackNumber = extractRackNumber(selectedRackForStorage.code);
    const locationText = (container.location || '').toLowerCase().replace(/\./g, '-');
    const nameText = (container.name || '').toLowerCase().replace(/\./g, '-');

    const mentionsRack = locationText.includes('rack') || nameText.includes('rack');

    if (mentionsRack) {
      const rackMatch = (locationText + ' ' + nameText).match(/rack[-_]?([\d\.\-]+)/i);
      if (rackMatch) {
        const mentionedRackNumber = rackMatch[1].replace(/\./g, '-');
        const isCurrentRack = mentionedRackNumber === currentRackNumber;
        const rackCode = mentionedRackNumber.includes('-')
          ? `RACK-${mentionedRackNumber.toUpperCase()}`
          : `RACK-${mentionedRackNumber.toUpperCase()}`;
        return { rackCode, isCurrentRack };
      }
    }

    return { rackCode: null, isCurrentRack: false };
  };

  const getModalItemDisplayName = (item: ContainerAsset): string => {
    if (item.manufacturer && item.model) {
      return `${item.manufacturer} ${item.model}`;
    }
    if (item.model) return item.model;
    if (item.asset_type) return item.asset_type;
    if (item.asset_tag) return item.asset_tag;
    return `Item ${item.id}`;
  };

  const getModalItemQuantity = (item: ContainerAsset): number => {
    if (item.custom_fields && typeof item.custom_fields === 'object' && 'quantity' in item.custom_fields) {
      return item.custom_fields.quantity as number;
    }
    return 1;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-xl">Loading {t('bins').toLowerCase()}...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('bin')} Visualizations</h1>
        <div className="flex items-center space-x-4">
          {/* View Mode Toggle */}
          <div className="flex items-center space-x-2 bg-gray-200 dark:bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1 rounded text-sm font-medium transition ${viewMode === 'grid'
                ? 'bg-card dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow'
                : 'text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-200'
                }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 rounded text-sm font-medium transition ${viewMode === 'list'
                ? 'bg-card dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow'
                : 'text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-200'
                }`}
            >
              List
            </button>
          </div>

          {/* Datacenter Filter */}
          <select
            value={filterDatacenter || ''}
            onChange={(e) => setFilterDatacenter(e.target.value ? parseInt(e.target.value) : null)}
            className="input"
          >
            <option value="">All {t('locations')}</option>
            {datacenters.map(dc => (
              <option key={dc.id} value={dc.id}>
                {dc.name} ({dc.code})
              </option>
            ))}
          </select>

          {isAuthenticated && (
            <button
              onClick={() => navigate('/locations')}
              className="btn-primary"
            >
              Manage {t('bins')}
            </button>
          )}
        </div>
      </div>

      {racks.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-lg shadow">
          <p className="text-gray-500 dark:text-gray-400 text-lg mb-4">No {t('bins').toLowerCase()} found</p>
          {isAuthenticated && (
            <button
              onClick={() => navigate('/locations')}
              className="btn-primary"
            >
              Create Your First {t('bin')}
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Overall Storage Summary Bar */}
          {(() => {
            // Filter containers by selected datacenter if one is selected
            const filteredContainers = filterDatacenter
              ? storageContainers.filter(container => {
                // Get room for this container to check its datacenter
                const room = rooms.find(r => r.id === container.room_id);
                return room && room.datacenter_id === filterDatacenter;
              })
              : storageContainers;

            const totalItems = filteredContainers.reduce((sum, container) => sum + (container.total_assets || 0), 0);
            const totalContainers = filteredContainers.length;
            if (totalItems > 0 || totalContainers > 0) {
              const navigateToStorage = () => {
                const params = new URLSearchParams();
                if (filterDatacenter) {
                  params.set('datacenter_id', filterDatacenter.toString());
                }
                navigate(`/storage${params.toString() ? '?' + params.toString() : ''}`);
              };

              return (
                <div
                  onClick={navigateToStorage}
                  className="mb-4 p-3 bg-card dark:bg-gray-800 rounded-lg shadow cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-semibold text-primary">
                      {totalItems} item{totalItems !== 1 ? 's' : ''} in {t('storage').toLowerCase()}
                    </span>
                    {totalContainers > 0 && (
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        ({totalContainers} {totalContainers !== 1 ? t('containers').toLowerCase() : t('container').toLowerCase()})
                      </span>
                    )}
                    {filterDatacenter && (
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        in {getDatacenterName(filterDatacenter)}
                      </span>
                    )}
                  </div>
                </div>
              );
            }
            return null;
          })()}

          <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
            Showing {racks.length} {racks.length !== 1 ? t('bins').toLowerCase() : t('bin').toLowerCase()}
            {filterDatacenter && ` in ${getDatacenterName(filterDatacenter)}`}
          </div>

          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {racks.map(rack => {
                const rackAssets = getRackAssets(rack.id);
                const storageInfo = getRackStorageInfo(rack);
                return (
                  <div
                    key={rack.id}
                    className="bg-card rounded-lg shadow-lg dark:shadow-gray-900 hover:shadow-xl dark:hover:shadow-gray-800 transition-shadow cursor-pointer"
                    onClick={() => navigate(`/racks/${rack.id}`)}
                  >
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="text-lg font-bold text-primary">{rack.code}</h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400">{rack.name}</p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/racks/${rack.id}`);
                          }}
                          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium"
                        >
                          View Details →
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                        <div>📍 {getDatacenterName(rack.datacenter_id)}</div>
                        {rack.room_id && <div>🏢 {getRoomName(rack.room_id)}</div>}
                        <div>📏 {rack.height_u}U {t('bin')}</div>
                        {rack.power_capacity_watts && (() => {
                          const powerInfo = getRackPowerInfo(rack);
                          return (
                            <div>⚡ {powerInfo.used.toFixed(1)} / {powerInfo.total.toFixed(1)} kW ({powerInfo.percentage}%)</div>
                          );
                        })()}
                        <div className="pt-1 space-y-1">
                          <div>
                            <span className="font-medium text-primary">
                              {rackAssets.length} device{rackAssets.length !== 1 ? 's' : ''} mounted
                            </span>
                          </div>
                          {storageInfo.items > 0 && (
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                openStorageModal(rack);
                              }}
                              className="cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                            >
                              <span className="font-medium text-primary">
                                📦 {storageInfo.items} item{storageInfo.items !== 1 ? 's' : ''} in {storageInfo.containers} {storageInfo.containers !== 1 ? t('containers').toLowerCase() : t('container').toLowerCase()}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="p-4">
                      <RackView
                        rackId={rack.id}
                        rackName={rack.name}
                        rackCode={rack.code}
                        rackSize={rack.height_u}
                        assets={assets}
                        onAssetClick={(asset) => {
                          navigate(`/assets/${asset.id}`);
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-4">
              {racks.map(rack => {
                const rackAssets = getRackAssets(rack.id);
                const storageInfo = getRackStorageInfo(rack);
                return (
                  <div
                    key={rack.id}
                    className="bg-card rounded-lg shadow-lg dark:shadow-gray-900 hover:shadow-xl dark:hover:shadow-gray-800 transition-shadow"
                  >
                    <div className="p-6">
                      <div className="flex flex-col lg:flex-row gap-6">
                        {/* Rack Info */}
                        <div className="lg:w-1/3">
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <h3 className="text-xl font-bold text-primary">{rack.code}</h3>
                              <p className="text-gray-500 dark:text-gray-400">{rack.name}</p>
                            </div>
                            <button
                              onClick={() => navigate(`/racks/${rack.id}`)}
                              className="btn-primary text-sm"
                            >
                              View Details
                            </button>
                          </div>
                          <div className="space-y-2 text-sm">
                            <div className="flex items-center text-gray-500 dark:text-gray-400">
                              <span className="font-medium w-24">{t('location')}:</span>
                              <span>{getDatacenterName(rack.datacenter_id)}</span>
                            </div>
                            {rack.room_id && (
                              <div className="flex items-center text-gray-500 dark:text-gray-400">
                                <span className="font-medium w-24">Room:</span>
                                <span>{getRoomName(rack.room_id)}</span>
                              </div>
                            )}
                            <div className="flex items-center text-gray-500 dark:text-gray-400">
                              <span className="font-medium w-24">Height:</span>
                              <span>{rack.height_u}U</span>
                            </div>
                            {rack.power_capacity_watts && (() => {
                              const powerInfo = getRackPowerInfo(rack);
                              return (
                                <div className="flex items-center text-gray-500 dark:text-gray-400">
                                  <span className="font-medium w-24">Power:</span>
                                  <span>{powerInfo.used.toFixed(1)} / {powerInfo.total.toFixed(1)} kW ({powerInfo.percentage}%)</span>
                                </div>
                              );
                            })()}
                            {rack.row && (
                              <div className="flex items-center text-gray-500 dark:text-gray-400">
                                <span className="font-medium w-24">Row:</span>
                                <span>{rack.row}</span>
                              </div>
                            )}
                            {rack.position && (
                              <div className="flex items-center text-gray-500 dark:text-gray-400">
                                <span className="font-medium w-24">Position:</span>
                                <span>{rack.position}</span>
                              </div>
                            )}
                            <div className="flex items-center text-primary pt-2 border-t dark:border-gray-700">
                              <span className="font-medium w-24">Devices:</span>
                              <span className="font-semibold">{rackAssets.length} mounted</span>
                            </div>
                            {storageInfo.items > 0 && (
                              <div
                                className="flex items-center text-primary cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openStorageModal(rack);
                                }}
                              >
                                <span className="font-medium w-24">Storage:</span>
                                <span className="font-semibold">
                                  📦 {storageInfo.items} item{storageInfo.items !== 1 ? 's' : ''} in {storageInfo.containers} {storageInfo.containers !== 1 ? t('containers').toLowerCase() : t('container').toLowerCase()}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Rack Visualization */}
                        <div className="lg:w-2/3">
                          <RackView
                            rackId={rack.id}
                            rackName={rack.name}
                            rackCode={rack.code}
                            rackSize={rack.height_u}
                            assets={assets}
                            onAssetClick={(asset) => {
                              navigate(`/assets/${asset.id}`);
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Storage Containers Modal */}
      {showStorageModal && selectedRackForStorage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowStorageModal(false)}>
          <div
            className="bg-card rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto m-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-card border-b border-gray-200 dark:border-gray-700 p-6 z-10">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold text-primary">Nearby {t('storage')}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {selectedRackForStorage.code} - {selectedRackForStorage.name}
                  </p>
                  {modalRoom && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      In {modalRoom.name} ({modalRoom.code})
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setShowStorageModal(false)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-2xl font-bold"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {modalContainers.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <p>No {t('containers').toLowerCase()} found in this room</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {modalContainers.map(container => {
                    const rackInfo = getModalContainerRackInfo(container);
                    const isExpanded = expandedContainers.has(container.id);
                    const items = containerItems.get(container.id) || [];
                    const isLoading = loadingItems.has(container.id);

                    return (
                      <div
                        key={container.id}
                        className="text-sm bg-subtle rounded border border-gray-200 dark:border-gray-600 overflow-hidden"
                      >
                        {/* Container Header - Clickable to expand/collapse */}
                        <div
                          onClick={() => toggleModalContainerExpansion(container.id)}
                          className="p-3 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {isExpanded ? '▼' : '▶'}
                              </span>
                              <div className="font-medium dark:text-gray-200">{container.name}</div>
                            </div>
                            {rackInfo.rackCode && !rackInfo.isCurrentRack && (
                              <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                                On {rackInfo.rackCode}
                              </span>
                            )}
                          </div>
                          <div className="text-gray-500 dark:text-gray-400 mt-1 ml-5">
                            <span className="font-medium">{container.total_assets} item{container.total_assets !== 1 ? 's' : ''}</span>
                            {' • '}
                            {container.container_type}
                            {container.location && !rackInfo.rackCode && ` • ${container.location}`}
                          </div>
                        </div>

                        {/* Expanded Content */}
                        {isExpanded && (
                          <div className="px-3 pb-3 pt-2 border-t border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800">
                            {isLoading ? (
                              <div className="text-xs text-gray-500 dark:text-gray-400 py-2">Loading items...</div>
                            ) : items.length === 0 ? (
                              <div className="text-xs text-gray-500 dark:text-gray-400 py-2">No items in this container</div>
                            ) : (
                              <div className="space-y-1">
                                {items.map((item, index) => {
                                  const quantity = getModalItemQuantity(item);
                                  const isLast = index === items.length - 1;
                                  const displayName = getModalItemDisplayName(item);
                                  const description = item.description || '';
                                  const isDescriptionExpanded = expandedDescriptions.has(item.id);
                                  const MAX_DESC_LENGTH = 50;
                                  const shouldTruncate = description.length > MAX_DESC_LENGTH;
                                  const truncatedDesc = shouldTruncate ? description.substring(0, MAX_DESC_LENGTH) + '...' : description;

                                  return (
                                    <div key={item.id} className="text-xs text-gray-500 dark:text-gray-400 pl-2 font-mono">
                                      {isLast ? '└──' : '├──'} {quantity > 1 ? `${quantity}x ` : ''}{displayName}
                                      {description && (
                                        <span className="text-gray-500 dark:text-gray-400 ml-2">
                                          ({isDescriptionExpanded || !shouldTruncate ? description : truncatedDesc}
                                          {shouldTruncate && !isDescriptionExpanded && (
                                            <button
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setExpandedDescriptions(prev => new Set(prev).add(item.id));
                                              }}
                                              className="text-blue-600 dark:text-blue-400 hover:underline ml-1"
                                            >
                                              [+]
                                            </button>
                                          )}
                                          {shouldTruncate && isDescriptionExpanded && (
                                            <button
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setExpandedDescriptions(prev => {
                                                  const newSet = new Set(prev);
                                                  newSet.delete(item.id);
                                                  return newSet;
                                                });
                                              }}
                                              className="text-blue-600 dark:text-blue-400 hover:underline ml-1"
                                            >
                                              [-]
                                            </button>
                                          )})
                                        </span>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* Quick Actions */}
                            <div className="flex gap-2 mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowStorageModal(false);
                                  navigate(`/storage-containers/${container.id}`);
                                }}
                                className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                              >
                                View Container
                              </button>
                              {isAuthenticated && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setShowStorageModal(false);
                                    navigate(`/storage-containers/${container.id}?action=scan-out`);
                                  }}
                                  className="text-xs px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                  Scan Item Out
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Racks;


