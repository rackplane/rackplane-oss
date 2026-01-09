// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { formatAssetType } from '../utils/formatAssetType';
import { formatStatus } from '../utils/formatStatus';

interface StorageBoxItem {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  manufacturer?: string;
  model?: string;
  description?: string;
  status: string;
}

interface StorageBoxItemsProps {
  containerId: number;
}

export const StorageBoxItems: React.FC<StorageBoxItemsProps> = ({ containerId }) => {
  const [items, setItems] = useState<StorageBoxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (containerId) {
      fetchItems();
    }
  }, [containerId]);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/v1/assets/containers/${containerId}/items`);
      setItems(response.data);
      setError(null);
    } catch (err: any) {
      logger.error('Error fetching storage box items:', err);
      setError(err.response?.data?.detail || 'Failed to load items');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading items...</div>;
  }

  if (error) {
    return <div className="text-sm text-red-600">Error: {error}</div>;
  }

  if (items.length === 0) {
    return <p className="text-sm text-gray-500">No items in this storage box.</p>;
  }

  return (
    <div className="mt-2">
      <h4 className="text-sm font-semibold text-gray-700 mb-2">
        Items in this box ({items.length}):
      </h4>
      <div className="space-y-2 max-h-60 overflow-y-auto">
        {items.map(item => {
          // Use description as primary name if available, otherwise use manufacturer/model or asset_tag
          const displayName = item.description ||
            (item.manufacturer && item.model ? `${item.manufacturer} ${item.model}` :
              item.manufacturer || item.model || item.asset_tag);

          return (
            <div key={item.id} className="bg-section-card p-2 rounded border border-default">
              <Link
                to={`/assets/${item.id}`}
                className="font-medium text-blue-600 hover:underline text-sm"
              >
                {displayName}
              </Link>
              <div className="text-xs text-gray-600 mt-1">
                {item.description && (item.manufacturer || item.model) && (
                  <>
                    {item.manufacturer && `${item.manufacturer} `}
                    {item.model && `${item.model} `}
                    <span className="text-gray-400">• </span>
                  </>
                )}
                <span className="text-gray-500">{formatAssetType(item.asset_type)}</span>
                {!item.description && (
                  <span className="text-gray-400 ml-1">• {item.asset_tag}</span>
                )}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Status: <span className="font-medium">{formatStatus(item.status)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

