// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import { formatAssetType } from '../utils/formatAssetType';

interface ItemType {
  item_type_key: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  count: number;
  items: Array<{
    id: number;
    asset_tag: string;
    serial_number: string;
    status: string;
  }>;
}

interface StorageBox {
  id: number;
  asset_tag?: string;  // Legacy: for Asset-based boxes
  name?: string;  // For StorageContainers
  model?: string;
  manufacturer?: string;
  description?: string;
  min_stock_threshold?: number;
  current_count?: number;
  is_low_stock?: boolean;
  item_types?: ItemType[];
  low_stock_types?: ItemType[];
  stock_summary?: any;
  isStorageContainer?: boolean;  // True for StorageContainer, false for Asset-based box
}

interface StorageBoxListProps {
  containerIds?: number[];  // Optional: filter to specific containers
}

const StorageBoxList: React.FC<StorageBoxListProps> = ({ containerIds }) => {
  const { t } = useWhiteLabel();
  const [boxes, setBoxes] = useState<StorageBox[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStorageBoxes();
  }, [containerIds]);

  const fetchStorageBoxes = async () => {
    try {
      setLoading(true);

      // Fetch both StorageContainers and Asset-based storage boxes
      const [containersResponse, assetBoxesResponse] = await Promise.all([
        axios.get(`${API_URL}/api/v1/storage-containers/`),
        axios.get(`${API_URL}/api/v1/assets/storage-boxes`).catch(() => ({ data: [] }))  // Graceful fallback
      ]);

      const containers = containersResponse.data || [];
      const assetBoxes = assetBoxesResponse.data || [];

      // Fetch stock summary for each StorageContainer
      const storageContainersWithStock = await Promise.all(
        containers.map(async (container: any) => {
          try {
            const stockResponse = await axios.get(
              `${API_URL}/api/v1/storage-containers/${container.id}/stock-summary`
            );
            const summary = stockResponse.data;

            return {
              ...container,
              asset_tag: container.name,  // Use name as asset_tag for compatibility
              current_count: summary.total_items,
              is_low_stock: summary.is_low_stock,
              stock_summary: summary,
              item_types: summary.item_types,
              low_stock_types: summary.low_stock_types,
              isStorageContainer: true,  // Mark as StorageContainer
            };
          } catch (err) {
            return {
              ...container,
              asset_tag: container.name,
              current_count: 0,
              is_low_stock: false,
              item_types: [],
              low_stock_types: [],
              isStorageContainer: true,
            };
          }
        })
      );

      // Fetch stock summary for each Asset-based storage box
      const assetBoxesWithStock = await Promise.all(
        assetBoxes.map(async (box: any) => {
          try {
            // Use the generic stock-summary endpoint that handles both types
            const stockResponse = await axios.get(
              `${API_URL}/api/v1/assets/containers/${box.id}/stock-summary`
            );
            const summary = stockResponse.data;

            return {
              id: box.id,
              name: box.asset_tag,  // Asset-based boxes use asset_tag as name
              asset_tag: box.asset_tag,
              description: box.description,
              current_count: summary.total_items,
              is_low_stock: summary.is_low_stock,
              stock_summary: summary,
              item_types: summary.item_types || [],
              low_stock_types: summary.low_stock_types || [],
              min_stock_threshold: box.min_stock_threshold,
              isStorageContainer: false,  // Mark as Asset-based box
            };
          } catch (err) {
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
      const allBoxes = [...storageContainersWithStock, ...assetBoxesWithStock];

      // Apply filter if containerIds provided
      const filtered = containerIds
        ? allBoxes.filter((box: StorageBox) => containerIds.includes(box.id))
        : allBoxes;

      setBoxes(filtered);
      setError(null);
    } catch (err: any) {
      logger.error('Error fetching storage boxes:', err);
      setError(err.response?.data?.detail || `Failed to load ${t('storage')} ${t('containers').toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-section-card">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading {t('storage')} {t('containers').toLowerCase()}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
      </div>
    );
  }

  if (boxes.length === 0) {
    return (
      <div className="bg-section-card">
        <p className="text-sm text-gray-500 dark:text-gray-400">No {t('storage')} {t('containers').toLowerCase()} found.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {boxes.map((box) => {
        const isLowStock = box.is_low_stock || false;
        const currentCount = box.current_count || 0;
        // Get threshold from item types (ContainerStockThreshold records)
        // No fallback to box.min_stock_threshold - that field is deprecated
        let minThreshold = 0;
        if (box.item_types && box.item_types.length > 0) {
          // Find the minimum threshold from all item types that have thresholds
          const thresholds = box.item_types
            .map((item: any) => item.min_threshold)
            .filter((t: any) => t && t > 0);
          if (thresholds.length > 0) {
            minThreshold = Math.min(...thresholds);
          }
        }

        return (
          <div
            key={box.id}
            className={`border p-4 rounded-lg shadow transition-all ${isLowStock
              ? 'border-red-500 dark:border-red-700 bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50'
              : 'border-default bg-card hover:bg-table-row-hover'
              }`}
          >
            <div className="flex items-start justify-between mb-2">
              <Link
                to={box.isStorageContainer !== false ? `/storage-containers/${box.id}` : `/assets/${box.id}`}
                className="font-bold text-gray-900 dark:text-gray-100 hover:text-primary dark:hover:text-accent"
              >
                {box.name || box.asset_tag}
              </Link>
              {isLowStock && (
                <span className="text-xs font-bold uppercase text-red-600 dark:text-red-400 bg-red-200 dark:bg-red-900/50 px-2 py-1 rounded">
                  ⚠ Low {t('stock')}
                </span>
              )}
            </div>

            {box.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                {box.description}
              </p>
            )}

            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total {t('items')}:</span>
                <span
                  className={`font-mono font-bold text-lg ${isLowStock ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                    }`}
                >
                  {currentCount}
                </span>
              </div>
              {minThreshold > 0 && (
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Minimum:</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">{minThreshold}</span>
                </div>
              )}

              {/* Show item types breakdown if available */}
              {box.item_types && box.item_types.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">{t('stock')} by {t('category')}:</p>
                  <div className="space-y-1">
                    {box.item_types.slice(0, 3).map((itemType: any, idx: number) => {
                      const itemThreshold = itemType.min_threshold; // Use item's own threshold, no fallback
                      const isItemLowStock = itemThreshold && itemThreshold > 0 && itemType.count < itemThreshold;
                      return (
                        <div key={idx} className="flex justify-between items-center text-xs">
                          <span className="text-gray-600 dark:text-gray-400 truncate flex-1 mr-2">
                            {itemType.manufacturer && `${itemType.manufacturer} `}
                            {itemType.model || formatAssetType(itemType.asset_type)}
                          </span>
                          <span className={`font-mono font-semibold ${isItemLowStock ? 'text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'
                            }`}>
                            {itemType.count}{itemThreshold && itemThreshold > 0 ? ` / ${itemThreshold}` : ''}
                          </span>
                        </div>
                      );
                    })}
                    {box.item_types.length > 3 && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                        +{box.item_types.length - 3} more type{box.item_types.length - 3 !== 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Progress bar */}
              {minThreshold > 0 && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${isLowStock ? 'bg-red-500 dark:bg-red-600' : 'bg-green-500 dark:bg-green-600'
                        }`}
                      style={{
                        width: `${Math.min((currentCount / minThreshold) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {isLowStock && (
              <div className="mt-3 pt-3 border-t border-red-200 dark:border-red-800">
                <p className="text-xs text-red-700 dark:text-red-300 font-semibold">
                  Reorder Required
                </p>
                {box.low_stock_types && box.low_stock_types.length > 0 ? (
                  <div className="mt-1 space-y-1">
                    {box.low_stock_types
                      .filter((itemType: any) => itemType.min_threshold && itemType.min_threshold > 0)
                      .map((itemType: any, idx: number) => {
                        // Use the item's own threshold - it should always be set for items in low_stock_types
                        const itemThreshold = itemType.min_threshold;
                        return (
                          <p key={idx} className="text-xs text-red-600 dark:text-red-400">
                            {itemType.manufacturer && `${itemType.manufacturer} `}
                            {itemType.model || formatAssetType(itemType.asset_type)}: {itemType.count} / {itemThreshold} (min: {itemThreshold})
                          </p>
                        );
                      })}
                  </div>
                ) : (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                    Only {currentCount} remaining{minThreshold > 0 ? ` (minimum: ${minThreshold})` : ''}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StorageBoxList;


