// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { formatStatus } from '../utils/formatStatus';
import { formatAssetType } from '../utils/formatAssetType';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  status: string;
  hostname?: string;
  description?: string;
  custom_fields?: {
    cable_length?: string;
    connector_type?: string;
    quantity?: number;
    // Fiber cable fields
    fiber_type?: string;
    fiber_connector_a?: string;
    fiber_connector_b?: string;
    fiber_breakout?: string;
    // DAC cable fields
    dac_connector_a?: string;
    dac_connector_b?: string;
    dac_breakout?: string;
    [key: string]: any;
  };
}

interface AssetTypeInfo {
  asset_type: string;
  display_name: string;
  count: number;
}

interface ContainerAssetTypes {
  container_id: number;
  container_name: string;
  asset_types: AssetTypeInfo[];
  total_assets: number;
}

interface ItemType {
  item_type_key: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  count: number;
  min_threshold?: number;
  max_quantity?: number;
  items: Array<{
    id: number;
    asset_tag: string;
    serial_number: string;
    status: string;
    description?: string;
    quantity?: number;
  }>;
}

interface StockSummary {
  container_id: number;
  container_name: string;
  min_threshold: number;
  total_items: number;
  item_types: ItemType[];
  low_stock_types: ItemType[];
  is_low_stock: boolean;
}

interface Rack {
  id: number;
  name: string;
  code: string;
  datacenter_id: number;
}

interface Datacenter {
  id: number;
  name: string;
  code: string;
}

const ContainerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t } = useWhiteLabel();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetTypesInfo, setAssetTypesInfo] = useState<ContainerAssetTypes | null>(null);
  const [stockSummary, setStockSummary] = useState<StockSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAssetType, setSelectedAssetType] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [editingQuantity, setEditingQuantity] = useState<number | null>(null);
  const [quantityValue, setQuantityValue] = useState<string>('');
  const [editingThreshold, setEditingThreshold] = useState<string | null>(null); // item_type_key
  const [minValue, setMinValue] = useState<string>('');
  const [maxValue, setMaxValue] = useState<string>('');
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [racks, setRacks] = useState<Rack[]>([]);
  const [showBulkAssignModal, setShowBulkAssignModal] = useState(false);
  const [bulkAssignRackId, setBulkAssignRackId] = useState<string>('');
  const [bulkAssignDatacenterId, setBulkAssignDatacenterId] = useState<string>('');
  const [bulkAssigning, setBulkAssigning] = useState(false);

  useEffect(() => {
    if (id) {
      fetchContainerAssetTypes();
      fetchStockSummary();
      fetchAssets();
      fetchDatacenters();
    }
  }, [id]);

  useEffect(() => {
    if (bulkAssignDatacenterId) {
      fetchRacks(parseInt(bulkAssignDatacenterId));
    } else {
      setRacks([]);
    }
  }, [bulkAssignDatacenterId]);

  const fetchDatacenters = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
    } catch (err: any) {
      logger.error('Failed to fetch datacenters:', err);
    }
  };

  const fetchRacks = async (datacenterId: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`, {
        params: { datacenter_id: datacenterId }
      });
      setRacks(response.data || []);
    } catch (err: any) {
      logger.error('Failed to fetch racks:', err);
      setRacks([]);
    }
  };

  useEffect(() => {
    if (id) {
      fetchAssets(selectedAssetType);
    }
  }, [selectedAssetType]);

  const fetchContainerAssetTypes = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/${id}/asset-types`);
      setAssetTypesInfo(response.data);
    } catch (err: any) {
      logger.error('Failed to fetch asset types:', err);
      setError(`Failed to load ${t('item').toLowerCase()} ${t('categories').toLowerCase()}`);
    }
  };

  const fetchStockSummary = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/${id}/stock-summary`);
      setStockSummary(response.data);
    } catch (err: any) {
      logger.error('Failed to fetch stock summary:', err);
    }
  };

  const fetchAssets = async (assetType?: string) => {
    try {
      setLoading(true);
      const params = assetType ? { asset_type: assetType } : {};
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/${id}/assets`, { params });
      setAssets(response.data || []);
    } catch (err: any) {
      logger.error('Failed to fetch assets:', err);
      setError(`Failed to load ${t('items').toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: string } = {
      active: 'badge-success',
      deployed: 'badge-success',
      maintenance: 'badge-warning',
      failed: 'badge-danger',
      decommissioned: 'badge-info',
      received: 'badge-info'
    };
    return `badge ${statusMap[status] || 'badge-info'}`;
  };

  const handleAssetTypeFilter = (assetType: string) => {
    setSelectedAssetType(assetType === selectedAssetType ? '' : assetType);
  };

  const getAssetTypeDisplayName = (assetTypeName: string): string => {
    if (!assetTypesInfo) return assetTypeName;
    const typeInfo = assetTypesInfo.asset_types.find(type => type.asset_type === assetTypeName);
    return typeInfo?.display_name || assetTypeName;
  };

  const getCableSpecifications = (asset: Asset): string => {
    const cf = asset.custom_fields;
    if (!cf) return '-';

    // Fiber cable specifications
    if (asset.asset_type === 'fiber_cable') {
      const parts: string[] = [];
      if (cf.fiber_type) parts.push(cf.fiber_type);
      if (cf.cable_length) parts.push(cf.cable_length);

      // Build connector description
      if (cf.fiber_connector_a && cf.fiber_connector_b) {
        if (cf.fiber_breakout) {
          parts.push(`${cf.fiber_connector_a} ${cf.fiber_breakout} ${cf.fiber_connector_b}`);
        } else {
          parts.push(`${cf.fiber_connector_a} → ${cf.fiber_connector_b}`);
        }
      } else if (cf.fiber_connector_a) {
        parts.push(cf.fiber_connector_a);
      }

      return parts.length > 0 ? parts.join(' | ') : '-';
    }

    // DAC cable specifications
    if (asset.asset_type === 'dac_cable') {
      const parts: string[] = [];
      if (cf.cable_length) parts.push(cf.cable_length);

      // Build connector description
      if (cf.dac_connector_a && cf.dac_connector_b) {
        if (cf.dac_breakout) {
          parts.push(`${cf.dac_connector_a} ${cf.dac_breakout} ${cf.dac_connector_b}`);
        } else {
          parts.push(`${cf.dac_connector_a} → ${cf.dac_connector_b}`);
        }
      } else if (cf.dac_connector_a) {
        parts.push(cf.dac_connector_a);
      }

      return parts.length > 0 ? parts.join(' | ') : '-';
    }

    // Other cable types or transceivers
    return cf.cable_length || cf.connector_type || '-';
  };

  const startEditingQuantity = (asset: Asset) => {
    setEditingQuantity(asset.id);
    setQuantityValue(asset.custom_fields?.quantity?.toString() || '1');
  };

  const cancelEditingQuantity = () => {
    setEditingQuantity(null);
    setQuantityValue('');
  };

  const saveQuantity = async (asset: Asset) => {
    try {
      const newQuantity = parseInt(quantityValue);
      if (isNaN(newQuantity) || newQuantity < 1) {
        alert('Please enter a valid quantity (minimum 1)');
        return;
      }

      // Update the asset with new quantity
      const updatedCustomFields = {
        ...asset.custom_fields,
        quantity: newQuantity
      };

      await axios.put(`${API_URL}/api/v1/assets/${asset.id}`, {
        ...asset,
        custom_fields: updatedCustomFields
      });

      // Refresh the asset list
      await fetchAssets(selectedAssetType);
      await fetchContainerAssetTypes(); // Refresh the summary too
      await fetchStockSummary(); // Refresh stock summary

      setEditingQuantity(null);
      setQuantityValue('');
    } catch (err: any) {
      logger.error('Failed to update quantity:', err);
      alert('Failed to update quantity: ' + (err.response?.data?.detail || err.message));
    }
  };

  const startEditingThreshold = (itemType: ItemType) => {
    setEditingThreshold(itemType.item_type_key);
    setMinValue(itemType.min_threshold?.toString() || '');
    setMaxValue(itemType.max_quantity?.toString() || '');
  };

  const cancelEditingThreshold = () => {
    setEditingThreshold(null);
    setMinValue('');
    setMaxValue('');
  };

  const saveThreshold = async (itemType: ItemType) => {
    try {
      const newMin = parseInt(minValue);
      const newMax = maxValue ? parseInt(maxValue) : null;

      if (isNaN(newMin) || newMin < 1) {
        alert('Please enter a valid minimum threshold (minimum 1)');
        return;
      }

      if (newMax !== null && (isNaN(newMax) || newMax < 1)) {
        alert('Please enter a valid maximum quantity (minimum 1)');
        return;
      }

      // Check if threshold already exists
      const thresholdsResponse = await axios.get(`${API_URL}/api/v1/storage-containers/${id}/stock-thresholds`);
      const existingThreshold = thresholdsResponse.data.find((t: any) =>
        t.asset_type === itemType.asset_type &&
        (t.manufacturer || '') === (itemType.manufacturer || '') &&
        (t.model || '') === (itemType.model || '')
      );

      const payload = {
        min_threshold: newMin,
        max_quantity: newMax
      };

      if (existingThreshold) {
        // Update existing threshold
        await axios.put(
          `${API_URL}/api/v1/storage-containers/${id}/stock-thresholds/${existingThreshold.id}`,
          payload
        );
      } else {
        // Create new threshold
        await axios.post(
          `${API_URL}/api/v1/storage-containers/${id}/stock-thresholds`,
          {
            asset_type: itemType.asset_type,
            manufacturer: itemType.manufacturer || null,
            model: itemType.model || null,
            ...payload
          }
        );
      }

      // Refresh stock summary
      await fetchStockSummary();

      setEditingThreshold(null);
      setMinValue('');
      setMaxValue('');
    } catch (err: any) {
      logger.error('Failed to save threshold:', err);
      alert('Failed to save threshold: ' + (err.response?.data?.detail || err.message));
    }
  };

  const deleteThreshold = async (itemType: ItemType) => {
    try {
      if (!window.confirm(`Remove stock threshold for ${itemType.manufacturer || ''} ${itemType.model || itemType.asset_type}?`)) {
        return;
      }

      // Get threshold ID
      const thresholdsResponse = await axios.get(`${API_URL}/api/v1/storage-containers/${id}/stock-thresholds`);
      const existingThreshold = thresholdsResponse.data.find((t: any) =>
        t.asset_type === itemType.asset_type &&
        (t.manufacturer || '') === (itemType.manufacturer || '') &&
        (t.model || '') === (itemType.model || '')
      );

      if (existingThreshold) {
        await axios.delete(
          `${API_URL}/api/v1/storage-containers/${id}/stock-thresholds/${existingThreshold.id}`
        );
        await fetchStockSummary();
      }
    } catch (err: any) {
      logger.error('Failed to delete threshold:', err);
      alert('Failed to delete threshold: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleBulkAssignToRack = async () => {
    if (!bulkAssignRackId) {
      alert(`Please select a ${t('bin').toLowerCase()}`);
      return;
    }

    if (!window.confirm(`Set the location of this ${t('storage').toLowerCase()} ${t('container').toLowerCase()} to the selected ${t('bin').toLowerCase()}? This will update the ${t('container').toLowerCase()}'s location, not individual ${t('items').toLowerCase()}.`)) {
      return;
    }

    setBulkAssigning(true);
    try {
      const rackId = parseInt(bulkAssignRackId);
      const datacenterId = parseInt(bulkAssignDatacenterId);

      // Get rack details to find room_id
      const rackResponse = await axios.get(`${API_URL}/api/v1/locations/racks/${rackId}`);
      const rack = rackResponse.data;

      // Update the storage container's location (room_id, datacenter_id, and location field)
      await axios.put(`${API_URL}/api/v1/storage-containers/${id}`, {
        room_id: rack.room_id,
        datacenter_id: datacenterId,
        location: `Bottom of ${t('bin').toLowerCase()} ${rack.code}`
      });

      // Refresh container info
      await fetchContainerAssetTypes();
      setShowBulkAssignModal(false);
      setBulkAssignRackId('');
      setBulkAssignDatacenterId('');
      alert(`Successfully set ${t('container').toLowerCase()} location to ${t('bin').toLowerCase()} ${rack.code}`);
    } catch (err: any) {
      logger.error('Failed to bulk assign to rack:', err);
      alert(`Failed to set ${t('container').toLowerCase()} location: ` + (err.response?.data?.detail || err.message));
    } finally {
      setBulkAssigning(false);
    }
  };

  if (error) {
    return (
      <div>
        <div className="flex items-center mb-8">
          <Link to="/storage" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mr-4">
            ← Back to {t('storage')}
          </Link>
        </div>
        <div className="card">
          <div className="text-red-600">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link to="/storage" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mb-2 inline-block">
            ← Back to {t('storage')}
          </Link>
          <h1 className="text-3xl font-bold text-primary">
            {assetTypesInfo ? assetTypesInfo.container_name : 'Loading...'}
          </h1>
          {assetTypesInfo && (
            <p className="text-gray-500 dark:text-gray-400 mt-2">
              Total {t('items')}: <span className="font-semibold">{assetTypesInfo.total_assets}</span>
            </p>
          )}
        </div>
        {assets.length > 0 && (
          <button
            onClick={() => setShowBulkAssignModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Bulk Assign to {t('bin')}
          </button>
        )}
      </div>

      {/* Stock Summary by Item Type */}
      {stockSummary && stockSummary.item_types && stockSummary.item_types.length > 0 && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-primary mb-4">Stock by {t('item')} {t('category')}</h2>
          <div className="space-y-3">
            {stockSummary.item_types.map((itemType) => {
              const isLowStock = itemType.min_threshold && itemType.count < itemType.min_threshold;
              const isEditing = editingThreshold === itemType.item_type_key;

              return (
                <div
                  key={itemType.item_type_key}
                  className={`p-4 rounded-lg border ${isLowStock
                    ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                    : 'bg-section-card border-default'
                    }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-primary">
                          {itemType.count}x
                        </span>
                        <span className="font-semibold text-primary">
                          {itemType.manufacturer && `${itemType.manufacturer} `}
                          {itemType.model || formatAssetType(itemType.asset_type)}
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                          ({formatAssetType(itemType.asset_type)})
                        </span>
                        {isLowStock && (
                          <span className="badge badge-error text-xs">⚠ Low Stock</span>
                        )}
                      </div>
                      <div className="mt-2 space-y-1">
                        {itemType.items.map((item) => (
                          <div key={item.id} className="flex items-start gap-2 text-sm">
                            <Link
                              to={`/assets/${item.id}`}
                              className="text-blue-600 dark:text-blue-400 hover:underline font-medium min-w-[100px]"
                            >
                              {item.asset_tag}
                            </Link>
                            <span className="text-gray-500 dark:text-gray-400 flex-1">
                              {item.description || '-'}
                            </span>
                            {item.quantity && item.quantity > 1 && (
                              <span className="text-gray-500 dark:text-gray-400 text-xs">
                                (qty: {item.quantity})
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="ml-4 text-right">
                      {isEditing ? (
                        <div className="flex flex-col gap-1 items-end">
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-gray-500">Min:</span>
                            <input
                              type="number"
                              value={minValue}
                              onChange={(e) => setMinValue(e.target.value)}
                              min="1"
                              className="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm w-16 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                              placeholder="Min"
                              autoFocus
                            />
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-gray-500">Max:</span>
                            <input
                              type="number"
                              value={maxValue}
                              onChange={(e) => setMaxValue(e.target.value)}
                              min="1"
                              className="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm w-16 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                              placeholder="Max"
                            />
                          </div>
                          <div className="flex gap-1 mt-1">
                            <button
                              onClick={() => saveThreshold(itemType)}
                              className="text-green-600 hover:text-green-800 text-xs px-1 border border-green-200 rounded"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditingThreshold}
                              className="text-red-600 hover:text-red-800 text-xs px-1 border border-red-200 rounded"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col items-end gap-1">
                          {itemType.min_threshold ? (
                            <>
                              <div className="text-sm">
                                <span className="text-gray-500 dark:text-gray-400">Min: </span>
                                <span className={`font-bold ${isLowStock ? 'text-red-600' : 'text-primary'}`}>
                                  {itemType.min_threshold}
                                </span>
                              </div>
                              {itemType.max_quantity && (
                                <div className="text-sm">
                                  <span className="text-gray-500 dark:text-gray-400">Max: </span>
                                  <span className="font-bold text-primary">
                                    {itemType.max_quantity}
                                  </span>
                                </div>
                              )}
                              <button
                                onClick={() => startEditingThreshold(itemType)}
                                className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                              >
                                Edit Levels
                              </button>
                              <button
                                onClick={() => deleteThreshold(itemType)}
                                className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                              >
                                Remove
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => startEditingThreshold(itemType)}
                              className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                            >
                              Set Levels
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Asset Type Summary Cards */}
      {assetTypesInfo && assetTypesInfo.asset_types.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {assetTypesInfo.asset_types.map((typeInfo) => (
            <div
              key={typeInfo.asset_type}
              onClick={() => handleAssetTypeFilter(typeInfo.asset_type)}
              className={`card cursor-pointer transition-all hover:shadow-lg ${selectedAssetType === typeInfo.asset_type
                ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'hover:bg-table-row-hover'
                }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold text-primary">{typeInfo.display_name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{formatAssetType(typeInfo.asset_type)}</p>
                </div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{typeInfo.count}</div>
              </div>
              {selectedAssetType === typeInfo.asset_type && (
                <div className="mt-2 text-sm text-blue-600 dark:text-blue-400 font-medium">
                  ✓ Filtering by this type
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Filter Info */}
      {selectedAssetType && (
        <div className="card mb-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
          <div className="flex justify-between items-center">
            <p className="text-blue-800 dark:text-blue-200">
              Filtering by: <span className="font-semibold">
                {assetTypesInfo?.asset_types.find(type => type.asset_type === selectedAssetType)?.display_name}
              </span>
            </p>
            <button
              onClick={() => setSelectedAssetType('')}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
            >
              Clear Filter
            </button>
          </div>
        </div>
      )}

      {/* Assets Table */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-500 dark:text-gray-400">Loading {t('items').toLowerCase()}...</div>
        </div>
      ) : assets.length === 0 ? (
        <div className="card">
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            {selectedAssetType
              ? `No ${t('items').toLowerCase()} of this ${t('category').toLowerCase()} in this ${t('container').toLowerCase()}`
              : `This ${t('container').toLowerCase()} is empty`}
          </div>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>{t('item')} Tag</th>
                <th>Serial Number</th>
                <th>{t('category')}</th>
                <th>Manufacturer</th>
                <th>Model</th>
                <th>Specifications</th>
                <th>Quantity</th>
                <th>Hostname</th>
                <th>Status</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td className="font-medium">{asset.asset_tag}</td>
                  <td>{asset.serial_number}</td>
                  <td>{getAssetTypeDisplayName(asset.asset_type)}</td>
                  <td>{asset.manufacturer || '-'}</td>
                  <td>{asset.model || '-'}</td>
                  <td className="text-sm">
                    {getCableSpecifications(asset)}
                  </td>
                  <td>
                    {editingQuantity === asset.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={quantityValue}
                          onChange={(e) => setQuantityValue(e.target.value)}
                          min="1"
                          className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-24 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                          autoFocus
                        />
                        <button
                          onClick={() => saveQuantity(asset)}
                          className="text-green-600 hover:text-green-800 text-sm"
                          title="Save"
                        >
                          ✓
                        </button>
                        <button
                          onClick={cancelEditingQuantity}
                          className="text-red-600 hover:text-red-800 text-sm"
                          title="Cancel"
                        >
                          ✗
                        </button>
                      </div>
                    ) : (
                      <span className="font-medium">
                        {asset.custom_fields?.quantity || '-'}
                      </span>
                    )}
                  </td>
                  <td>{asset.hostname || '-'}</td>
                  <td>
                    <span className={getStatusBadge(asset.status)}>
                      {formatStatus(asset.status)}
                    </span>
                  </td>
                  <td className="max-w-xs truncate">{asset.description || '-'}</td>
                  <td>
                    {asset.custom_fields?.quantity && editingQuantity !== asset.id && (
                      <button
                        onClick={() => startEditingQuantity(asset)}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm"
                      >
                        Edit Qty
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Showing {assets.length} {selectedAssetType ? 'filtered ' : ''}{t('items').toLowerCase()}
            </p>
          </div>
        </div>
      )}

      {/* Bulk Assign to Rack Modal */}
      {showBulkAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h2 className="text-xl font-bold text-primary mb-4">Bulk Assign to {t('bin')}</h2>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Assign all {assets.length} {t('items').toLowerCase()} in this {t('container').toLowerCase()} to a {t('bin').toLowerCase()} {t('location').toLowerCase()}.
              </p>

              <div className="space-y-4">
                {/* Datacenter Selection */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('location')}
                  </label>
                  <select
                    value={bulkAssignDatacenterId}
                    onChange={(e) => {
                      setBulkAssignDatacenterId(e.target.value);
                      setBulkAssignRackId(''); // Reset rack when datacenter changes
                    }}
                    className="input w-full"
                  >
                    <option value="">-- Select {t('location')} --</option>
                    {datacenters.map(dc => (
                      <option key={dc.id} value={dc.id}>
                        {dc.name} ({dc.code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Rack Selection */}
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    {t('bin')}
                  </label>
                  <select
                    value={bulkAssignRackId}
                    onChange={(e) => setBulkAssignRackId(e.target.value)}
                    className="input w-full"
                    disabled={!bulkAssignDatacenterId}
                  >
                    <option value="">-- Select {t('bin')} --</option>
                    {racks
                      .filter(rack => !bulkAssignDatacenterId || rack.datacenter_id === parseInt(bulkAssignDatacenterId))
                      .map(rack => (
                        <option key={rack.id} value={rack.id}>
                          {rack.name} ({rack.code})
                        </option>
                      ))}
                  </select>
                  {!bulkAssignDatacenterId && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Select a {t('location').toLowerCase()} first
                    </p>
                  )}
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => {
                    setShowBulkAssignModal(false);
                    setBulkAssignRackId('');
                    setBulkAssignDatacenterId('');
                  }}
                  className="px-4 py-2 border border-default rounded-lg hover:bg-table-row-hover"
                  disabled={bulkAssigning}
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkAssignToRack}
                  disabled={!bulkAssignRackId || bulkAssigning}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {bulkAssigning ? 'Assigning...' : `Assign ${assets.length} ${t('items')}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContainerDetail;
