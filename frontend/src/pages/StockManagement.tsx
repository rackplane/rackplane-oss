// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import StorageBoxList from '../components/StorageBoxList';
import logger from '../utils/logger';

const StockManagement: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { t } = useWhiteLabel();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'boxes' | 'low-stock'>('overview');
  const [lowStockBoxes, setLowStockBoxes] = useState<any[]>([]);
  const [totalContainers, setTotalContainers] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchLowStockBoxes();
    }
  }, [isAuthenticated]);

  const fetchLowStockBoxes = async () => {
    try {
      setLoading(true);
      setFetchError(null);

      // Fetch both StorageContainers and Asset-based storage boxes
      // Track errors separately so we can show appropriate UI state
      let containersError = false;
      let assetBoxesError = false;

      const [containersResponse, assetBoxesResponse] = await Promise.all([
        axios.get(`${API_URL}/api/v1/storage-containers/`).catch((err) => {
          logger.error('Error fetching storage-containers:', err);
          containersError = true;
          return { data: [] };
        }),
        axios.get(`${API_URL}/api/v1/assets/storage-boxes`).catch((err) => {
          logger.error('Error fetching assets/storage-boxes:', err);
          assetBoxesError = true;
          return { data: [] };
        })
      ]);

      // If both endpoints failed, show error state
      if (containersError && assetBoxesError) {
        setFetchError('Failed to load storage containers. Please try again.');
      }

      const containers = containersResponse.data || [];
      const assetBoxes = assetBoxesResponse.data || [];

      logger.debug(`Fetched ${containers.length} storage containers and ${assetBoxes.length} asset boxes`);

      setTotalContainers(containers.length + assetBoxes.length);

      // Fetch stock summary for each StorageContainer
      const storageContainersWithStock = await Promise.all(
        containers.map(async (container: any) => {
          try {
            const stockResponse = await axios.get(
              `${API_URL}/api/v1/storage-containers/${container.id}/stock-summary`
            );
            const summary = stockResponse.data;
            if (summary.is_low_stock || (summary.low_stock_types && summary.low_stock_types.length > 0)) {
              logger.debug(`Low stock detected for ${container.name}:`, {
                is_low_stock: summary.is_low_stock,
                low_stock_types_count: summary.low_stock_types?.length || 0,
                low_stock_types: summary.low_stock_types
              });
            }
            return {
              ...container,
              asset_tag: container.name,
              current_count: summary.total_items,
              is_low_stock: summary.is_low_stock,
              stock_summary: summary,
              item_types: summary.item_types,
              low_stock_types: summary.low_stock_types || [],
              isStorageContainer: true,
            };
          } catch (err) {
            return null;
          }
        })
      );

      // Fetch stock summary for each Asset-based storage box
      const assetBoxesWithStock = await Promise.all(
        assetBoxes.map(async (box: any) => {
          try {
            const stockResponse = await axios.get(
              `${API_URL}/api/v1/assets/containers/${box.id}/stock-summary`
            );
            const summary = stockResponse.data;
            if (summary.is_low_stock || (summary.low_stock_types && summary.low_stock_types.length > 0)) {
              logger.debug(`Low stock detected for asset box ${box.asset_tag}:`, {
                is_low_stock: summary.is_low_stock,
                low_stock_types_count: summary.low_stock_types?.length || 0
              });
            }
            return {
              id: box.id,
              name: box.asset_tag,
              asset_tag: box.asset_tag,
              description: box.description,
              current_count: summary.total_items,
              is_low_stock: summary.is_low_stock,
              stock_summary: summary,
              item_types: summary.item_types || [],
              low_stock_types: summary.low_stock_types || [],
              min_stock_threshold: box.min_stock_threshold,
              isStorageContainer: false,
            };
          } catch (err) {
            // If stock endpoint fails, check if threshold is set
            return {
              id: box.id,
              name: box.asset_tag,
              asset_tag: box.asset_tag,
              description: box.description,
              current_count: 0,
              is_low_stock: box.min_stock_threshold > 0,  // Low stock if threshold set but no items
              item_types: [],
              low_stock_types: [],
              min_stock_threshold: box.min_stock_threshold,
              isStorageContainer: false,
            };
          }
        })
      );

      // Combine both types
      const allBoxesWithStock = [...storageContainersWithStock, ...assetBoxesWithStock];

      // Filter to only containers that are low stock
      const lowStock = allBoxesWithStock.filter(
        (box: any) => {
          if (!box) return false;
          const isLow = box.is_low_stock || (box.low_stock_types && box.low_stock_types.length > 0);
          if (isLow) {
            logger.debug(`Including ${box.name} in low stock list:`, {
              is_low_stock: box.is_low_stock,
              low_stock_types_count: box.low_stock_types?.length || 0
            });
          }
          return isLow;
        }
      );
      logger.debug(`Found ${lowStock.length} low stock containers`);
      setLowStockBoxes(lowStock);
    } catch (err: any) {
      logger.error('Error fetching low stock boxes:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500 dark:text-gray-400">Please log in to view stock management.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-primary">{t('stock')} Management</h1>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/assets')}
            className="btn-primary bg-blue-600 hover:bg-blue-700"
          >
            Manage {t('items')}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {fetchError && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
          <span className="text-red-600 dark:text-red-400">⚠️</span>
          <span className="text-red-700 dark:text-red-300">{fetchError}</span>
          <button
            onClick={fetchLowStockBoxes}
            className="ml-auto text-sm text-red-600 dark:text-red-400 hover:underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'overview'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('boxes')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'boxes'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
          >
            All {t('containers')}
          </button>
          <button
            onClick={() => setActiveTab('low-stock')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'low-stock'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
          >
            Low Stock Alerts
            {lowStockBoxes.length > 0 && (
              <span className="ml-2 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {lowStockBoxes.length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-card shadow rounded-lg p-6">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total {t('containers')}</h3>
              <p className="text-3xl font-bold text-primary">
                {loading ? '...' : totalContainers}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">See "All {t('containers')}" tab for details</p>
            </div>
            <div className="bg-card shadow rounded-lg p-6">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Low {t('stock')} Alerts</h3>
              <p className="text-3xl font-bold text-red-600 dark:text-red-400">{lowStockBoxes.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Requires immediate attention</p>
            </div>
            <div className="bg-card shadow rounded-lg p-6">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">{t('stock')} Status</h3>
              <p className="text-sm text-primary">
                {lowStockBoxes.length === 0 ? (
                  <span className="text-green-600 dark:text-green-400 font-semibold">All {t('stock')} Levels OK</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400 font-semibold">Action Required</span>
                )}
              </p>
            </div>
          </div>

          {/* Quick Info */}
          <div className="bg-card shadow rounded-lg p-6">
            <h2 className="text-xl font-bold text-primary mb-4">How {t('stock')} Management Works</h2>
            <div className="space-y-3 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-start">
                <span className="font-semibold text-blue-600 dark:text-blue-400 mr-2">1.</span>
                <p>
                  Create a {t('container').toLowerCase()} (e.g., "{t('container')} 1", "Shelf A") and set a <code className="bg-subtle px-1 rounded">min_stock_threshold</code> (and optional <code className="bg-subtle px-1 rounded">max_quantity</code>) value.
                </p>
              </div>
              <div className="flex items-start">
                <span className="font-semibold text-blue-600 dark:text-blue-400 mr-2">2.</span>
                <p>
                  Add {t('items').toLowerCase()} to the {t('container').toLowerCase()} by setting their <code className="bg-subtle px-1 rounded">storage_container_id</code> and <code className="bg-subtle px-1 rounded">status = IN_STORAGE</code>.
                </p>
              </div>
              <div className="flex items-start">
                <span className="font-semibold text-blue-600 dark:text-blue-400 mr-2">3.</span>
                <p>
                  When you check out an {t('item').toLowerCase()} (or scan it), it automatically moves from <code className="bg-subtle px-1 rounded">IN_STORAGE</code> to <code className="bg-subtle px-1 rounded">DEPLOYED</code> and is removed from the {t('container').toLowerCase()}.
                </p>
              </div>
              <div className="flex items-start">
                <span className="font-semibold text-blue-600 dark:text-blue-400 mr-2">4.</span>
                <p>
                  The system automatically checks {t('stock').toLowerCase()} levels and alerts you when inventory drops below the minimum threshold.
                </p>
              </div>
            </div>
          </div>

          {/* Recent Low Stock (if any) */}
          {lowStockBoxes.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-red-800 dark:text-red-300 mb-4">⚠️ Low {t('stock')} Alerts</h2>
              <div className="space-y-2">
                {lowStockBoxes.slice(0, 5).map((box: any) => (
                  <div key={box.id} className="flex justify-between items-center bg-card p-3 rounded">
                    <Link
                      to={box.isStorageContainer !== false ? `/storage-containers/${box.id}` : `/assets/${box.id}`}
                      className="font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {box.name}
                    </Link>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {box.current_count} / {box.low_stock_types && box.low_stock_types.length > 0
                        ? box.low_stock_types[0].min_threshold || 'N/A'
                        : (box.item_types && box.item_types.length > 0 && box.item_types[0].min_threshold) || 'N/A'} (minimum)
                    </span>
                  </div>
                ))}
                {lowStockBoxes.length > 5 && (
                  <button
                    onClick={() => setActiveTab('low-stock')}
                    className="text-sm text-red-600 dark:text-red-400 hover:underline font-semibold"
                  >
                    View all {lowStockBoxes.length} low {t('stock').toLowerCase()} {t('items').toLowerCase()} →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'boxes' && (
        <div>
          <div className="mb-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              All {t('containers').toLowerCase()} with {t('stock').toLowerCase()} level tracking enabled. Click on any {t('container').toLowerCase()} to view details.
            </p>
          </div>
          <StorageBoxList />
        </div>
      )}

      {activeTab === 'low-stock' && (
        <div>
          {loading ? (
            <div className="text-center py-8">Loading low {t('stock').toLowerCase()} alerts...</div>
          ) : lowStockBoxes.length === 0 ? (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-8 text-center">
              <p className="text-lg font-semibold text-green-800 dark:text-green-300 mb-2">✅ All {t('stock')} Levels OK</p>
              <p className="text-sm text-green-600 dark:text-green-400">
                No {t('containers').toLowerCase()} are currently below their minimum {t('stock').toLowerCase()} threshold.
              </p>
            </div>
          ) : (
            <div>
              <div className="mb-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {lowStockBoxes.length} {lowStockBoxes.length !== 1 ? t('containers').toLowerCase() : t('container').toLowerCase()} require{'s'} immediate attention.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {lowStockBoxes.map((box: any) => (
                  <div
                    key={box.id}
                    className="border-2 border-red-500 dark:border-red-600 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg shadow"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Link
                        to={box.isStorageContainer !== false ? `/storage-containers/${box.id}` : `/assets/${box.id}`}
                        className="font-bold text-primary hover:text-blue-600 dark:hover:text-blue-400"
                      >
                        {box.name || box.asset_tag}
                      </Link>
                      <span className="text-xs font-bold uppercase text-red-600 dark:text-red-400 bg-red-200 dark:bg-red-800 px-2 py-1 rounded">
                        ⚠ Low {t('stock')}
                      </span>
                    </div>
                    {box.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                        {box.description}
                      </p>
                    )}
                    <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-800">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-primary font-semibold">Total {t('items')}:</span>
                        <span className="font-mono font-bold text-lg text-red-600 dark:text-red-400">
                          {box.current_count || 0}
                        </span>
                      </div>
                      {/* Get display threshold from low_stock_types or container global */}
                      {(() => {
                        // Get threshold from low_stock_types first, then from item_types
                        const displayThreshold = box.low_stock_types && box.low_stock_types.length > 0
                          ? box.low_stock_types[0].min_threshold
                          : (box.item_types && box.item_types.length > 0 && box.item_types[0].min_threshold) || 0;
                        return displayThreshold > 0 ? (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-primary font-semibold">Minimum Required:</span>
                            <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">{displayThreshold}</span>
                          </div>
                        ) : null;
                      })()}

                      {/* Show low stock items with their specific thresholds */}
                      {box.low_stock_types && box.low_stock_types.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-red-200 dark:border-red-800">
                          <p className="text-xs font-semibold text-red-700 dark:text-red-300 mb-2">Low {t('stock')} {t('items')}:</p>
                          <div className="space-y-1">
                            {box.low_stock_types
                              .filter((item: any) => item.min_threshold && item.min_threshold > 0)
                              .map((item: any, idx: number) => (
                                <p key={idx} className="text-xs text-red-600 dark:text-red-400">
                                  {item.manufacturer && `${item.manufacturer} `}
                                  {item.model || item.asset_type}: {item.count} / {item.min_threshold} (min: {item.min_threshold})
                                </p>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Show item types breakdown if available */}
                      {box.item_types && box.item_types.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-red-200 dark:border-red-800">
                          <p className="text-xs font-semibold text-primary mb-2">{t('stock')} by {t('item')} Type:</p>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {box.item_types.map((itemType: any, idx: number) => {
                              const itemThreshold = itemType.min_threshold;
                              const isLow = itemThreshold && itemThreshold > 0 && itemType.count < itemThreshold;
                              return (
                                <div key={idx} className={`flex justify-between items-center text-xs p-1 rounded ${isLow ? 'bg-red-100 dark:bg-red-900/30' : 'bg-subtle'
                                  }`}>
                                  <span className="text-primary truncate flex-1 mr-2">
                                    {itemType.manufacturer && `${itemType.manufacturer} `}
                                    {itemType.model || itemType.asset_type}
                                  </span>
                                  <span className={`font-mono font-semibold ${isLow ? 'text-red-700 dark:text-red-400' : 'text-primary'
                                    }`}>
                                    {itemType.count}{itemThreshold && itemThreshold > 0 ? ` / ${itemThreshold}` : ''}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {(() => {
                        // Get threshold from low_stock_types first, then from item_types
                        const displayThreshold = box.low_stock_types && box.low_stock_types.length > 0
                          ? box.low_stock_types[0].min_threshold
                          : (box.item_types && box.item_types.length > 0 && box.item_types[0].min_threshold) || 0;
                        return displayThreshold > 0 ? (
                          <>
                            <div className="mt-3">
                              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div
                                  className="h-2 rounded-full bg-red-500 dark:bg-red-600"
                                  style={{
                                    width: `${Math.min(((box.current_count || 0) / displayThreshold) * 100, 100)}%`,
                                  }}
                                />
                              </div>
                            </div>
                            <p className="text-xs text-red-700 dark:text-red-400 font-semibold mt-3">
                              Reorder Required - Only {box.current_count || 0} remaining (minimum: {displayThreshold})
                            </p>
                          </>
                        ) : (
                          <p className="text-xs text-red-700 dark:text-red-400 font-semibold mt-3">
                            Reorder Required - Only {box.current_count || 0} remaining
                          </p>
                        );
                      })()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StockManagement;

