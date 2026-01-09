// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { RackView, isPositionAvailable, getAvailablePositions } from '../components/RackView';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import logger from '../utils/logger';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number?: string;  // Make optional to match RackView interface
  manufacturer?: string;
  model?: string;
  description?: string;
  hostname?: string;
  rack_id?: number;
  rack_position_start?: number;
  rack_position_end?: number;
  height_u?: number;
  status?: string;
  asset_type?: string;
  custom_fields?: any;  // For quantity and other custom data
}

interface Rack {
  id: number;
  name: string;
  code: string;
  height_u: number;
  datacenter_id: number;
  room_id?: number;
  power_capacity_watts?: number;
}

interface StorageContainer {
  id: number;
  name: string;
  container_type: string;
  location?: string;
  description?: string;
  room_id?: number;
  total_assets: number;
}

interface Room {
  id: number;
  name: string;
  code: string;
  datacenter_id: number;
}

const RackDetail: React.FC = () => {
  const { rackId } = useParams<{ rackId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { t } = useWhiteLabel();
  const [rack, setRack] = useState<Rack | null>(null);
  const [room, setRoom] = useState<Room | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [storageContainers, setStorageContainers] = useState<StorageContainer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [showPositionModal, setShowPositionModal] = useState(false);
  const [newPosition, setNewPosition] = useState<{ start: number; height: number } | null>(null);
  // Inline expansion state for storage containers
  const [expandedContainers, setExpandedContainers] = useState<Set<number>>(new Set());
  const [containerItems, setContainerItems] = useState<Map<number, Asset[]>>(new Map());
  const [loadingItems, setLoadingItems] = useState<Set<number>>(new Set());
  const [expandedDescriptions, setExpandedDescriptions] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (rackId) {
      fetchRackDetails();
      fetchRackAssets();
    }
  }, [rackId]);

  useEffect(() => {
    if (rack?.room_id) {
      fetchRoomDetails(rack.room_id);
      fetchStorageContainers();
    }
  }, [rack?.room_id]);

  // Scroll to storage section if hash is present
  useEffect(() => {
    if (window.location.hash === '#storage' && storageContainers.length > 0) {
      setTimeout(() => {
        const element = document.getElementById('storage');
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }, [storageContainers.length]);

  const fetchRackDetails = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks/${rackId}`);
      setRack(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load rack details');
    } finally {
      setLoading(false);
    }
  };

  const fetchRoomDetails = async (roomId: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/rooms/${roomId}`);
      setRoom(response.data);
      logger.debug('Fetched room details:', response.data);
    } catch (err: any) {
      logger.error('Failed to load room details:', err);
      // Don't set error, room is optional context
    }
  };

  const fetchRackAssets = async () => {
    try {
      const rackIdNum = parseInt(rackId || '0', 10);
      logger.debug('Fetching assets for rack:', rackIdNum, 'rackId from URL:', rackId);
      const response = await axios.get(`${API_URL}/api/v1/assets/`, {
        params: { rack_id: rackIdNum, limit: 1000 }
      });
      logger.debug('Fetched assets:', response.data.assets?.length || 0, 'assets:', response.data.assets);
      setAssets(response.data.assets || []);
    } catch (err: any) {
      logger.error('Failed to load rack assets:', err);
      setAssets([]);
    }
  };

  const fetchStorageContainers = async () => {
    if (!rack?.room_id) return;
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/`, {
        params: { limit: 1000 }
      });

      // Show ALL containers in the same room (not just ones matching this specific rack)
      const containersInRoom = response.data.filter((container: StorageContainer) => {
        // Only show containers in the same room
        return container.room_id === rack.room_id;
      });

      logger.debug(`Found ${containersInRoom.length} containers in room ${rack.room_id} (showing all containers in same room)`);
      setStorageContainers(containersInRoom);
    } catch (err: any) {
      logger.error('Failed to load storage containers:', err);
      setStorageContainers([]);
    }
  };

  // Fetch container items when expanded
  const fetchContainerItems = async (containerId: number) => {
    if (containerItems.has(containerId)) {
      // Already loaded
      return;
    }

    setLoadingItems((prev: Set<number>) => new Set(prev).add(containerId));
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/${containerId}/assets`);
      setContainerItems((prev: Map<number, Asset[]>) => {
        const newMap = new Map(prev);
        newMap.set(containerId, response.data);
        return newMap;
      });
    } catch (err: any) {
      logger.error('Failed to load container items:', err);
      setContainerItems((prev: Map<number, Asset[]>) => {
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

  // Toggle container expansion
  const toggleContainerExpansion = (containerId: number) => {
    setExpandedContainers((prev: Set<number>) => {
      const newSet = new Set(prev);
      if (newSet.has(containerId)) {
        newSet.delete(containerId);
      } else {
        newSet.add(containerId);
        // Fetch items when expanding
        fetchContainerItems(containerId);
      }
      return newSet;
    });
  };

  // Format item display name
  const getItemDisplayName = (item: Asset): string => {
    if (item.manufacturer && item.model) {
      return `${item.manufacturer} ${item.model}`;
    }
    if (item.model) return item.model;
    if (item.asset_type) return item.asset_type;
    if (item.asset_tag) return item.asset_tag;
    return `${t('item')} ${item.id}`;
  };

  // Get item quantity (from custom_fields or default to 1)
  const getItemQuantity = (item: Asset): number => {
    if (item.custom_fields && typeof item.custom_fields === 'object' && 'quantity' in item.custom_fields) {
      return item.custom_fields.quantity as number;
    }
    return 1;
  };

  // Helper function to detect which rack a container is associated with
  const getContainerRackInfo = (container: StorageContainer): { rackCode: string | null; isCurrentRack: boolean } => {
    if (!rack) return { rackCode: null, isCurrentRack: false };

    const extractRackNumber = (code: string): string => {
      const normalized = code.toLowerCase();
      if (normalized.includes('rack-')) {
        return normalized.split('rack-')[1].replace(/\./g, '-');
      } else if (normalized.includes('rack')) {
        return normalized.split('rack')[1].replace(/\./g, '-').replace(/^-+/, '');
      }
      return normalized.replace(/\./g, '-');
    };

    const currentRackNumber = extractRackNumber(rack.code);
    const locationText = (container.location || '').toLowerCase().replace(/\./g, '-');
    const nameText = (container.name || '').toLowerCase().replace(/\./g, '-');

    // Check if container mentions a rack
    const mentionsRack = locationText.includes('rack') || nameText.includes('rack');

    if (mentionsRack) {
      // Try to extract rack code from location or name
      const rackMatch = (locationText + ' ' + nameText).match(/rack[-_]?([\d\.\-]+)/i);
      if (rackMatch) {
        const mentionedRackNumber = rackMatch[1].replace(/\./g, '-');
        const isCurrentRack = mentionedRackNumber === currentRackNumber;
        // Try to reconstruct rack code (e.g., "RACK-8-31" or "RACK-2")
        const rackCode = mentionedRackNumber.includes('-')
          ? `RACK-${mentionedRackNumber.toUpperCase()}`
          : `RACK-${mentionedRackNumber.toUpperCase()}`;
        return { rackCode, isCurrentRack };
      }
    }

    return { rackCode: null, isCurrentRack: false };
  };

  const handleAssetClick = (asset: Asset) => {
    logger.debug('RackDetail: handleAssetClick called for asset:', asset.id, asset.asset_tag);
    setSelectedAsset(asset);
    logger.debug('RackDetail: Navigating to /assets/' + asset.id);
    navigate(`/assets/${asset.id}`);
  };

  const handleUnitClick = (unit: number) => {
    if (!isAuthenticated) return;

    // Show modal to assign asset to this position
    setNewPosition({ start: unit, height: 1 });
    setShowPositionModal(true);
  };

  const handleUpdateAssetPosition = async (assetId: number, startU: number, heightU: number) => {
    try {
      // Check collision before updating
      if (!isPositionAvailable(rack!.id, startU, heightU, assets, assetId)) {
        alert(`Position U${startU}-${startU + heightU - 1} is already occupied. Please choose a different position.`);
        return;
      }

      const endU = startU + heightU - 1;
      await axios.put(`${API_URL}/api/v1/assets/${assetId}`, {
        rack_id: rack!.id,
        rack_position_start: startU,
        rack_position_end: endU,
        height_u: heightU
      });

      // Refresh assets
      await fetchRackAssets();
      setShowPositionModal(false);
      setNewPosition(null);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to update asset position';
      alert(errorMsg);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-xl">Loading {t('bin').toLowerCase()} details...</div>
      </div>
    );
  }

  if (error || !rack) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || `${t('bin')} not found`}</p>
          <button
            onClick={() => navigate('/locations')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Back to {t('locations')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <button
          onClick={() => navigate('/locations')}
          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mb-4"
        >
          ← Back to {t('locations')}
        </button>
        <h1 className="text-3xl font-bold text-primary">{rack.code} - {rack.name}</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-2">
          {rack.height_u}U {t('bin')} • {assets.filter(a => a.rack_position_start && a.rack_position_start >= 1).length} {t('item').toLowerCase()}(s) mounted
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rack Visualization */}
        <div className="lg:col-span-2">
          <RackView
            rackId={rack.id}
            rackName={rack.name}
            rackCode={rack.code}
            rackSize={rack.height_u}
            assets={assets}
            onAssetClick={handleAssetClick}
            onUnitClick={isAuthenticated ? handleUnitClick : undefined}
            showAssetListOnHover={false}
          />
        </div>

        {/* Rack Information & Actions */}
        <div className="space-y-4">
          <div className="bg-card rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-primary mb-3">{t('bin')} Information</h2>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Code</dt>
                <dd className="font-medium dark:text-gray-200">{rack.code}</dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Name</dt>
                <dd className="font-medium dark:text-gray-200">{rack.name}</dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Height</dt>
                <dd className="font-medium dark:text-gray-200">{rack.height_u}U</dd>
              </div>
              {rack.power_capacity_watts && (
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Power Capacity</dt>
                  <dd className="font-medium dark:text-gray-200">{(rack.power_capacity_watts / 1000).toFixed(1)} kW</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Available Positions */}
          {isAuthenticated && (
            <div className="bg-card rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-primary mb-3">Quick Actions</h2>
              <button
                onClick={() => navigate(`/assets?rack_id=${rack.id}`)}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 mb-2"
              >
                View All {t('items')} in {t('bin')}
              </button>
              <button
                onClick={() => navigate(`/assets?rack_id=${rack.id}&status=staging`)}
                className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Add {t('item')} to {t('bin')}
              </button>
            </div>
          )}

          {/* Installed Devices Summary */}
          <div className="bg-card rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-primary mb-3">Installed {t('items')}</h2>
            {assets.filter(a => a.rack_position_start && a.rack_position_start >= 1).length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No {t('items').toLowerCase()} mounted in this {t('bin').toLowerCase()}</p>
            ) : (
              <div className="space-y-2">
                {assets
                  .filter(a => a.rack_position_start && a.rack_position_start >= 1)
                  .sort((a, b) => {
                    // Sort top-down: highest rack_position_start first (U42 before U1)
                    const aPos = a.rack_position_start || 0;
                    const bPos = b.rack_position_start || 0;
                    return bPos - aPos; // Descending order
                  })
                  .map(asset => (
                    <div
                      key={asset.id}
                      onClick={() => handleAssetClick(asset)}
                      className="text-sm p-2 bg-subtle hover:bg-table-row-hover rounded cursor-pointer border border-default"
                    >
                      <div className="font-medium dark:text-gray-200">
                        {asset.manufacturer && asset.model
                          ? `${asset.manufacturer} ${asset.model}`
                          : asset.model || asset.asset_type || asset.asset_tag || t('item')
                        }
                      </div>
                      {asset.hostname && (
                        <div className="text-blue-600 dark:text-blue-400 text-xs font-mono mt-0.5">
                          {asset.hostname}
                        </div>
                      )}
                      {asset.asset_tag && (
                        <div className="text-gray-500 dark:text-gray-400 text-xs font-mono">
                          {asset.asset_tag}
                        </div>
                      )}
                      <div className="text-gray-500 dark:text-gray-400">
                        U{asset.rack_position_start}
                        {asset.rack_position_end && asset.rack_position_end !== asset.rack_position_start
                          ? `-${asset.rack_position_end}`
                          : ''}
                      </div>
                      {asset.description && (
                        <div className="text-gray-500 dark:text-gray-400 text-xs mt-1 line-clamp-2 opacity-80">
                          {asset.description}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Storage Containers in Room */}
          {storageContainers.length > 0 && (
            <div id="storage" className="bg-card rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-primary mb-3">{t('storage')} {t('containers')}</h2>
              {room && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  In {room.name} ({room.code})
                </p>
              )}
              {!room && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  {t('containers')} in the same room as this {t('bin').toLowerCase()}
                </p>
              )}
              <div className="space-y-2">
                {storageContainers.map(container => {
                  const rackInfo = getContainerRackInfo(container);
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
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleContainerExpansion(container.id);
                        }}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
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
                          <span className="font-medium">{container.total_assets} {t('item').toLowerCase()}{container.total_assets !== 1 ? 's' : ''}</span>
                          {' • '}
                          {container.container_type}
                          {container.location && !rackInfo.rackCode && ` • ${container.location}`}
                        </div>
                      </div>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="px-2 pb-2 pt-1 border-t border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800">
                          {isLoading ? (
                            <div className="text-xs text-gray-500 dark:text-gray-400 py-2">Loading {t('items').toLowerCase()}...</div>
                          ) : items.length === 0 ? (
                            <div className="text-xs text-gray-500 dark:text-gray-400 py-2">No {t('items').toLowerCase()} in this {t('container').toLowerCase()}</div>
                          ) : (
                            <div className="space-y-1">
                              {items.map((item, index) => {
                                const quantity = getItemQuantity(item);
                                const isLast = index === items.length - 1;
                                const displayName = getItemDisplayName(item);
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
                                navigate(`/storage-containers/${container.id}`);
                              }}
                              className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                              View {t('container')}
                            </button>
                            {isAuthenticated && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  // TODO: Implement scan item out functionality
                                  navigate(`/storage-containers/${container.id}?action=scan-out`);
                                }}
                                className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                              >
                                Scan {t('item')} Out
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Position Assignment Modal */}
      {showPositionModal && newPosition && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold dark:text-gray-100 mb-4">Assign {t('item')} to Position</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Select an {t('item').toLowerCase()} to assign to U{newPosition.start}
            </p>

            {/* List of assets not in a rack or in staging */}
            <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
              {assets
                .filter(a => !a.rack_id || a.status === 'staging')
                .map(asset => (
                  <button
                    key={asset.id}
                    onClick={() => {
                      const height = asset.height_u || 1;
                      handleUpdateAssetPosition(asset.id, newPosition.start, height);
                    }}
                    className="w-full text-left p-2 bg-subtle hover:bg-table-row-hover rounded border border-default"
                  >
                    <div className="font-medium dark:text-gray-200">{asset.asset_tag}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{asset.manufacturer} {asset.model}</div>
                  </button>
                ))}
            </div>

            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowPositionModal(false);
                  setNewPosition(null);
                }}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-200"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RackDetail;

