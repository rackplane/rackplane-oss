// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
// ImageUploadOCR is now imported in AssetFormModal
import BarcodeScanner from '../components/BarcodeScanner';
import SKUMatchModal from '../components/SKUMatchModal';
import LabelPrintModal from '../components/LabelPrintModal';
import PowerEfficiencyModal from '../components/PowerEfficiencyModal';
import AssetFilters from '../components/assets/AssetFilters';
import AssetTable from '../components/assets/AssetTable';
import AssetFormModal from '../components/assets/AssetFormModal';
import AssetBulkEditModal from '../components/assets/AssetBulkEditModal';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
// getAvailablePositions is now imported in AssetFormModal
import logger from '../utils/logger';
import { useAssetData } from '../hooks/useAssetData';
import { useAssetForm } from '../hooks/useAssetForm';
import {
  Asset,
  AssetType,
} from '../types/asset';
import {
  MAX_QUICK_FILTER_BUTTONS,
} from '../constants/assetOptions';
import { formatError } from '../utils/errorFormatters';

// Types and constants are now imported from '../types/asset' and '../constants/assetOptions'

const Assets: React.FC = () => {

  const { isAuthenticated } = useAuth();
  const { t, verticalPack, hasFeature } = useWhiteLabel();
  const navigate = useNavigate();

  // Asset data hook - consolidates all data fetching
  const {
    assets,
    assetTypes,
    datacenters,
    racks,
    rooms,
    storageContainers,
    portTemplates,
    loading,
    fetchAssets,
    fetchPortTemplates,
  } = useAssetData();

  const [search, setSearch] = useState('');

  // Asset form hook - consolidates form state, validation, and submission
  const {
    formData,
    setFormData,
    editingAsset,
    // setEditingAsset is available but unused - keeping for future use
    showModal,
    saving,
    error,
    setError,
    uploadedImageUrl,
    setUploadedImageUrl,
    useManualSerial,
    setUseManualSerial,
    skuLookupLoading,
    skuLookupError,
    skuAutocompleteSuggestions,
    showSkuAutocomplete,
    setShowSkuAutocomplete,
    openAddModal,
    openEditModal,
    closeModal,
    handleInputChange,
    handleSubmit,
    handleOCRComplete,
    handleOCRClear,
    handleSKULookup,
    fetchSkuAutocomplete,
    handleSkuAutocompleteSelect,
    shouldShowField,
  } = useAssetForm({
    assets,
    assetTypes,
    datacenters,
    racks,
    rooms,
    storageContainers,
    fetchAssets,
  });

  // Optimized Quick Filters Computation
  // Get top 5 asset types for quick filters
  // Renamed from topAssetTypes to clarify purpose
  const topAssetTypeFilters = React.useMemo(() => {
    const typeCounts: Record<string, number> = {};
    assets.forEach(asset => {
      // Normalize type name for grouping (display format)
      // We keep original casing for display but could normalize if data is messy
      const type = asset.asset_type;
      typeCounts[type] = (typeCounts[type] || 0) + 1;
    });

    return Object.entries(typeCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, MAX_QUICK_FILTER_BUTTONS)
      .map(([type, count]) => ({ type, count }));
  }, [assets]);

  // Non-form UI state
  const [sortColumn, setSortColumn] = useState<keyof Asset | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [hideStorageBoxes, setHideStorageBoxes] = useState<boolean>(true); // Default to hiding storage boxes from inventory
  const [selectedAssets, setSelectedAssets] = useState<number[]>([]);
  const [showBulkEditModal, setShowBulkEditModal] = useState(false);
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);
  const [showLabelPrint, setShowLabelPrint] = useState(false);
  const [printingAsset, setPrintingAsset] = useState<Asset | null>(null);
  const [showSKUMatchModal, setShowSKUMatchModal] = useState(false);
  const [ocrDetectedText, setOcrDetectedText] = useState<string>('');
  const [showPowerEfficiencyModal, setShowPowerEfficiencyModal] = useState(false);

  // Port template state (portTemplates comes from useAssetData hook)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [overwritePorts, setOverwritePorts] = useState(false);

  // Propagation state - setter unused until modal supports it
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [propagateToMatching, _setPropagateToMatching] = useState(false);

  // Calculate matching assets for the currently edited asset
  // Matches based on: Manufacturer + Model + Asset Type
  // Excludes the asset itself
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const matchingAssets = useMemo(() => {
    if (!editingAsset) return [];

    // Safety check - if basic identifying fields are missing, don't match
    if (!formData.asset_type || !formData.manufacturer || !formData.model) return [];

    return assets.filter(a =>
      a.id !== editingAsset.id && // Exclude self
      a.asset_type === formData.asset_type &&
      a.manufacturer === formData.manufacturer &&
      a.model === formData.model
    );
  }, [assets, editingAsset, formData.asset_type, formData.manufacturer, formData.model]);
  const [bulkEditData, setBulkEditData] = useState({
    datacenter_id: '',
    rack_id: '',
    storage_container_id: '',
    status: '',
    asset_type: '',
    // Cable connector end types
    dac_connector_a: '',
    dac_connector_b: '',
    // Fiber cable fields
    fiber_connector_a: '',
    fiber_connector_b: '',
    fiber_type: '',
    // Transceiver fields
    transceiver_type: '',
    fiber_connector: '',
    // Ethernet cable fields
    ethernet_category: '',
  });

  /**
   * Memoized analysis of selected asset types for bulk edit modal.
   * This replaces the inline IIFE in the bulk edit modal for better readability.
   */
  const bulkEditAssetTypeInfo = useMemo(() => {
    const selectedAssetObjects = assets.filter(a => selectedAssets.includes(a.id));
    const assetTypes = Array.from(new Set(selectedAssetObjects.map(a => a.asset_type?.toLowerCase())));

    return {
      allAreDACCables: assetTypes.length === 1 && assetTypes[0] === 'dac_cable',
      allAreFiberCables: assetTypes.length === 1 &&
        (assetTypes[0] === 'fiber_cable' || assetTypes[0] === 'aoc_cable'),
      allAreTransceivers: assetTypes.length === 1 &&
        (assetTypes[0] === 'transceiver' || assetTypes[0] === 'optical_transceiver'),
      allAreEthernetCables: assetTypes.length === 1 && assetTypes[0] === 'ethernet_cable',
      allAreCables: assetTypes.length === 1 &&
        ['dac_cable', 'fiber_cable', 'aoc_cable', 'ethernet_cable', 'power_cable'].includes(assetTypes[0] || ''),
    };
  }, [assets, selectedAssets]);

  // State for expanded groups in grouped view
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Toggle group expansion
  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

  // Select all assets in a group
  const handleSelectGroup = (groupAssets: Asset[], isSelected: boolean) => {
    if (isSelected) {
      // Add all group assets to selection
      setSelectedAssets(prev => {
        const groupIds = groupAssets.map(a => a.id);
        const newSelection = new Set([...prev, ...groupIds]);
        return Array.from(newSelection);
      });
    } else {
      // Remove all group assets from selection
      setSelectedAssets(prev => {
        const groupIds = new Set(groupAssets.map(a => a.id));
        return prev.filter(id => !groupIds.has(id));
      });
    }
  };

  // Note: availableRackPositions and getFormLocationValue are now in AssetFormModal
  const [searchParams, setSearchParams] = useSearchParams();

  // Debounce search to prevent too many API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAssets(search);
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [search, fetchAssets]);

  // Note: Initial data load (asset types, datacenters, racks, etc.) is handled by useAssetData hook

  // Handle ?edit=<id> URL parameter - opens edit modal for specific asset
  useEffect(() => {
    const editId = searchParams.get('edit');
    if (editId && assets.length > 0) {
      const assetToEdit = assets.find(a => a.id === parseInt(editId, 10));
      if (assetToEdit) {
        openEditModal(assetToEdit);
        // Clear the edit parameter from URL
        setSearchParams({}, { replace: true });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, assets]);

  // Handle ?modal=create URL parameter - opens create modal with pre-populated fields from VendorSKUs
  useEffect(() => {
    const modalParam = searchParams.get('modal');
    if (modalParam === 'create' && !showModal) {
      // Pre-populate form fields from URL parameters
      const manufacturer = searchParams.get('manufacturer') || '';
      const model = searchParams.get('model') || '';
      const asset_type = searchParams.get('asset_type') || '';
      const sku = searchParams.get('sku') || '';

      // Use openAddModal to initialize, then set the form data with URL params
      openAddModal();

      // Set pre-populated fields after modal opens
      setFormData(prev => ({
        ...prev,
        asset_type: asset_type,
        manufacturer: manufacturer,
        model: model,
        sku: sku,
      }));

      // Clear URL parameters after opening modal
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, showModal]);


  // Note: Rack position calculation is now handled inside AssetFormModal


  // Note: All data fetching functions (fetchAssets, fetchAssetTypes, etc.) are now provided by useAssetData hook

  // Validate asset_type when modal opens or assetTypes change
  useEffect(() => {
    if (showModal && formData.asset_type && assetTypes.length > 0) {
      const validType = assetTypes.find((t: AssetType) => t.name === formData.asset_type);
      if (!validType) {
        // Reset to empty string so user must select a valid type
        setFormData(prev => ({ ...prev, asset_type: '' }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showModal, formData.asset_type, assetTypes]);

  const handleBarcodeScan = async (decodedText: string) => {
    try {
      // Try to parse as JSON first (QR code with full asset data)
      try {
        const data = JSON.parse(decodedText);
        if (data.id) {
          // Navigate to asset detail page
          navigate(`/assets/${data.id}`);
          setShowBarcodeScanner(false);
          return;
        }
      } catch (e) {
        // Not JSON, treat as asset tag or serial number
      }

      // Try lookup by asset tag
      try {
        const response = await axios.get(`${API_URL}/api/v1/barcodes/lookup/${decodedText}`);
        navigate(`/assets/${response.data.id}`);
        setShowBarcodeScanner(false);
        return;
      } catch (e) {
        // Try lookup by serial number
        try {
          const response = await axios.get(`${API_URL}/api/v1/barcodes/lookup-serial/${decodedText}`);
          navigate(`/assets/${response.data.id}`);
          setShowBarcodeScanner(false);
          return;
        } catch (e2) {
          setError('Asset not found');
          setShowBarcodeScanner(false);
        }
      }
    } catch (err) {
      logger.error('Error processing barcode:', err);
      setError('Error processing barcode');
      setShowBarcodeScanner(false);
    }
  };


  // Note: openAddModal, openEditModal, closeModal, handleOCRComplete, handleOCRClear
  // are now provided by the useAssetForm hook

  // Extended handleOCRComplete with SKU match modal logic (wraps hook's handleOCRComplete)
  // Used by AssetFormModal when OCR finds FS.com indicators
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleOCRCompleteWithSKUMatch = React.useCallback((ocrResult: any, imageUrl: string) => {
    // Call the hook's OCR handler
    handleOCRComplete(ocrResult, imageUrl);

    // Check if this might be an FS.com product and show SKU match modal
    const rawText = ocrResult.raw_text || '';
    const parsed = ocrResult.parsed_data;
    const allText = `${rawText} ${parsed.model || ''} ${parsed.manufacturer || ''} ${parsed.part_number || ''}`.toLowerCase();

    // Look for FS.com indicators
    const hasFSIndicators =
      allText.includes('fs.com') ||
      allText.includes('fs ') ||
      (parsed.manufacturer && parsed.manufacturer.toLowerCase().includes('fs'));

    // Look for SKU patterns (6-digit numbers, SKU: patterns, etc.)
    const hasSKUPattern = /\b\d{5,7}\b/.test(rawText) || /SKU[:\s]+\d+/.test(rawText) || /fs\.com\/products\/\d+/.test(rawText);

    if (hasFSIndicators || hasSKUPattern) {
      setOcrDetectedText(rawText);
      setShowSKUMatchModal(true);
    }
  }, [handleOCRComplete]);


  const handleSKUSelected = (sku: any) => {
    // Auto-populate form with SKU data
    const specs = sku.specifications || {};

    setFormData(prev => ({
      ...prev,
      manufacturer: sku.manufacturer || prev.manufacturer,
      model: sku.name || prev.model,
      asset_type: sku.asset_type || prev.asset_type,
      sku: sku.sku || prev.sku,
      // Map specifications to form fields
      dac_speed: specs.speed || specs.dac_speed || prev.dac_speed,
      dac_connector_a: specs.connector_a || specs.dac_connector_a || prev.dac_connector_a,
      dac_connector_b: specs.connector_b || specs.dac_connector_b || prev.dac_connector_b,
      dac_breakout: specs.breakout || specs.dac_breakout || prev.dac_breakout,
      cable_length: specs.length || specs.cable_length || prev.cable_length,
      connector_type: specs.connector_type || prev.connector_type,
      fiber_type: specs.fiber_mode || specs.fiber_type || prev.fiber_type,
      fiber_connector_a: specs.connector_a || specs.fiber_connector_a || prev.fiber_connector_a,
      fiber_connector_b: specs.connector_b || specs.fiber_connector_b || prev.fiber_connector_b,
    }));

    setShowSKUMatchModal(false);
  };


  // Note: skuLookupLoading, skuLookupError, skuAutocompleteSuggestions, showSkuAutocomplete,
  // fetchSkuAutocomplete, handleSKULookup, handleInputChange, handleSkuAutocompleteSelect,
  // handleSubmit, and shouldShowField are now provided by the useAssetForm hook

  // Local state for bulk operations
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [bulkSaving, setBulkSaving] = useState(false);

  const handleDelete = async (assetId: number) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/assets/${assetId}`);
      await fetchAssets();
    } catch (err: any) {
      logger.error('Error deleting asset:', err);
      const errorDetail = err.response?.data?.detail || err.message;
      alert('Failed to delete asset: ' + formatError(errorDetail));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedAssets.length === 0) {
      alert('Please select at least one asset to delete');
      return;
    }

    const confirmMessage = `Are you sure you want to delete ${selectedAssets.length} asset(s)?\n\nThis action cannot be undone.`;
    if (!window.confirm(confirmMessage)) {
      return;
    }

    setBulkSaving(true);
    setError(null);

    try {
      const response = await axios.post(`${API_URL}/api/v1/assets/bulk-delete`, selectedAssets);
      const result = response.data;

      if (result.deleted_count > 0) {
        alert(result.message || `Successfully deleted ${result.deleted_count} asset(s).`);
        setSelectedAssets([]);
        await fetchAssets();
      } else {
        alert('No assets were deleted.');
      }
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail || error.message;
      setError('Failed to delete assets: ' + formatError(errorDetail));
      alert('Failed to delete assets: ' + formatError(errorDetail));
    } finally {
      setBulkSaving(false);
    }
  };

  const handleSort = (column: keyof Asset) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const getSortIndicator = (column: keyof Asset) => {
    if (sortColumn !== column) return ' ↕';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };


  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: string } = {
      active: 'badge-success',
      deployed: 'badge-success',
      maintenance: 'badge-warning',
      failed: 'badge-danger',
      decommissioned: 'badge-info'
    };
    return `badge ${statusMap[status] || 'badge-info'}`;
  };

  const getAssetTypeDisplayName = (assetTypeName: string): string => {
    const assetType = assetTypes.find(type => type.name === assetTypeName);
    return assetType?.display_name || assetTypeName;
  };

  const getDatacenterName = (datacenterId?: number): string => {
    if (!datacenterId) return '-';
    const datacenter = datacenters.find(dc => dc.id === datacenterId);
    return datacenter ? datacenter.name : '-';
  };

  const getLocationDisplay = (asset: Asset): string => {
    // If in a storage container, show container name
    if (asset.storage_container_id) {
      const container = storageContainers.find(c => c.id === asset.storage_container_id);
      if (container) {
        return container.name;
      }
    }
    // If deployed in a rack, show rack location with unit position
    if (asset.rack_id) {
      const rack = racks.find(r => r.id === asset.rack_id);
      if (rack) {
        const location = rack.name;
        if (asset.rack_position_start) {
          // Show rack name with unit position range
          return `${location} - U${asset.rack_position_start}${asset.rack_position_end && asset.rack_position_end !== asset.rack_position_start ? `-${asset.rack_position_end}` : ''}`;
        }
        // Asset is in rack but unit position not set - show rack name with note
        return `${location} - U?`;
      }
    }
    // Legacy storage location
    if (asset.storage_location) {
      return asset.storage_location;
    }
    return '-';
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedAssets(filteredAssets.map(asset => asset.id));
    } else {
      setSelectedAssets([]);
    }
  };

  const handleSelectAsset = (assetId: number) => {
    if (selectedAssets.includes(assetId)) {
      setSelectedAssets(selectedAssets.filter(id => id !== assetId));
    } else {
      setSelectedAssets([...selectedAssets, assetId]);
    }
  };

  const openBulkEditModal = () => {
    if (selectedAssets.length === 0) {
      alert('Please select at least one asset to edit');
      return;
    }
    setBulkEditData({
      datacenter_id: '',
      rack_id: '',
      storage_container_id: '',
      status: '',
      asset_type: '',
      dac_connector_a: '',
      dac_connector_b: '',
      fiber_connector_a: '',
      fiber_connector_b: '',
      fiber_type: '',
      transceiver_type: '',
      fiber_connector: '',
      ethernet_category: '',
    });
    // Reset and fetch port templates
    setSelectedTemplateId(null);
    setOverwritePorts(false);
    fetchPortTemplates();
    setShowBulkEditModal(true);
  };

  const closeBulkEditModal = () => {
    setShowBulkEditModal(false);
  };

  const handleBulkEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBulkSaving(true);
    setError(null);

    try {
      // Build the update payload - only include fields that were set
      const updatePayload: any = {};
      if (bulkEditData.datacenter_id) updatePayload.datacenter_id = parseInt(bulkEditData.datacenter_id);
      if (bulkEditData.rack_id) updatePayload.rack_id = parseInt(bulkEditData.rack_id);
      if (bulkEditData.storage_container_id) updatePayload.storage_container_id = parseInt(bulkEditData.storage_container_id);
      if (bulkEditData.status) updatePayload.status = bulkEditData.status;
      if (bulkEditData.asset_type) updatePayload.asset_type = bulkEditData.asset_type;

      // Handle formal connector updates (moving away from custom_fields)
      if (bulkEditData.dac_connector_a) updatePayload.connector_type_end_a = bulkEditData.dac_connector_a;
      if (bulkEditData.dac_connector_b) updatePayload.connector_type_end_b = bulkEditData.dac_connector_b;
      if (bulkEditData.fiber_connector_a) updatePayload.connector_type_end_a = bulkEditData.fiber_connector_a;
      if (bulkEditData.fiber_connector_b) updatePayload.connector_type_end_b = bulkEditData.fiber_connector_b;
      if (bulkEditData.ethernet_category) {
        updatePayload.connector_type_end_a = bulkEditData.ethernet_category;
        updatePayload.connector_type_end_b = bulkEditData.ethernet_category;
      }

      // Handle remaining cable/transceiver properties via custom_fields
      if (bulkEditData.fiber_type || bulkEditData.transceiver_type || bulkEditData.fiber_connector) {
        updatePayload.custom_fields = {
          ...(bulkEditData.fiber_type && { fiber_type: bulkEditData.fiber_type }),
          ...(bulkEditData.transceiver_type && { transceiver_type: bulkEditData.transceiver_type }),
          ...(bulkEditData.fiber_connector && { fiber_connector: bulkEditData.fiber_connector }),
        };
      }

      // Update each selected asset
      await Promise.all(
        selectedAssets.map(assetId =>
          axios.put(`${API_URL}/api/v1/assets/${assetId}`, updatePayload)
        )
      );

      // Apply port template if selected
      if (selectedTemplateId) {
        const templateResults = await Promise.allSettled(
          selectedAssets.map(assetId =>
            axios.post(`${API_URL}/api/v1/port-templates/apply`, {
              asset_id: assetId,
              template_id: selectedTemplateId,
              overwrite: overwritePorts
            })
          )
        );

        const successCount = templateResults.filter(r => r.status === 'fulfilled').length;
        const failCount = templateResults.filter(r => r.status === 'rejected').length;

        if (failCount > 0) {
          alert(`Template applied to ${successCount} assets.${failCount} failed.`);
        } else {
          alert(`Successfully applied template to all ${successCount} assets!`);
        }
      }

      await fetchAssets();
      setSelectedAssets([]);
      closeBulkEditModal();
    } catch (err: any) {
      logger.error('Error updating assets:', err);
      const errorDetail = err.response?.data?.detail || 'Failed to update assets';
      setError(formatError(errorDetail));
    } finally {
      setBulkSaving(false);
    }
  };

  const normalizedTypeFilter = typeFilter ? typeFilter.toLowerCase() : '';

  const filteredAssets = assets
    .filter(asset => {
      // Hide storage boxes if toggle is enabled
      if (hideStorageBoxes && asset.asset_type === 'storage_box') {
        return false;
      }

      // REMOVED: Client-side text search (now handled by backend)
      // The 'assets' array now only contains items matching the search term from the API

      // Type filter - case-insensitive partial matching
      // Special handling for 'nic' filter to include DPUs and cards
      const matchesType = !normalizedTypeFilter || (
        normalizedTypeFilter === 'nic'
          ? (asset.asset_type.toLowerCase().includes('nic') ||
            asset.asset_type.toLowerCase().includes('dpu') ||
            asset.asset_type.toLowerCase().includes('card'))
          : asset.asset_type.toLowerCase().includes(normalizedTypeFilter)
      );

      // Status filter - case-insensitive exact matching
      const matchesStatus = !statusFilter || asset.status.toLowerCase() === statusFilter.toLowerCase();

      return matchesType && matchesStatus;
    })
    .sort((a, b) => {
      if (!sortColumn) return 0;

      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle null/undefined values
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // Compare values
      let comparison = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.toLowerCase().localeCompare(bVal.toLowerCase());
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

  // Determine which columns should be visible based on filtered data
  const shouldShowColumn = (columnName: string): boolean => {
    if (filteredAssets.length === 0) return true; // Show all columns if no data

    switch (columnName) {
      case 'hostname':
        // Show hostname column only if at least one filtered asset has a hostname
        return filteredAssets.some(asset => asset.hostname && asset.hostname.trim() !== '');
      case 'serial_number':
      case 'asset_tag':
        // Hide serial number and asset tag for cables
        return !filteredAssets.every(asset => asset.asset_type.toLowerCase().includes('cable'));
      case 'quantity':
        // Show quantity column only if at least one asset has quantity
        return filteredAssets.some(asset => asset.custom_fields?.quantity && asset.custom_fields.quantity > 0);
      default:
        return true;
    }
  };

  /**
   * Helper to resolve an asset's datacenter ID by checking:
   * 1. Asset's direct datacenter_id
   * 2. Asset's rack's datacenter_id
   * 3. Asset's storage container's datacenter_id (or its room's datacenter_id)
   * 
   * This replaces inline IIFEs in the table render for better readability.
   */
  const getAssetDatacenterId = (asset: Asset): number | undefined => {
    if (asset.datacenter_id) return asset.datacenter_id;

    if (asset.rack_id) {
      const rack = racks.find(r => r.id === asset.rack_id);
      if (rack) return rack.datacenter_id;
    }

    if (asset.storage_container_id) {
      const container = storageContainers.find(c => c.id === asset.storage_container_id);
      if (container) {
        if (container.datacenter_id) return container.datacenter_id;
        if (container.room_id) {
          const room = rooms.find(r => r.id === container.room_id);
          if (room) return room.datacenter_id;
        }
      }
    }

    return undefined;
  };

  // Group assets by type + manufacturer + model + status for collapsed view
  interface AssetGroup {
    key: string;
    assets: Asset[];
    assetType: string;
    manufacturer: string;
    model: string;
    status: string;
  }

  const groupedAssets = useMemo(() => {
    const groups = new Map<string, AssetGroup>();

    filteredAssets.forEach(asset => {
      const key = `${asset.asset_type} | ${asset.manufacturer || ''} | ${asset.model || ''} | ${asset.status}`;

      if (groups.has(key)) {
        groups.get(key)!.assets.push(asset);
      } else {
        groups.set(key, {
          key,
          assets: [asset],
          assetType: asset.asset_type,
          manufacturer: asset.manufacturer || '',
          model: asset.model || '',
          status: asset.status,
        });
      }
    });

    return Array.from(groups.values());
  }, [filteredAssets]);

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('item')} {t('stock')}</h1>
        <div className="flex gap-3">
          {isAuthenticated && selectedAssets.length > 0 && (
            <div className="flex gap-3">
              <button
                onClick={openBulkEditModal}
                className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition text-base font-medium min-h-[44px]"
              >
                Edit Selected ({selectedAssets.length})
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={saving}
                className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 transition text-base font-medium min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Deleting...' : `Delete Selected(${selectedAssets.length})`}
              </button>
            </div>
          )}
          {isAuthenticated && (
            <>
              <button onClick={openAddModal} className="btn-primary">+ Add {t('item')}</button>
              <button
                onClick={() => setShowBarcodeScanner(true)}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
                title="Scan barcode"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
                </svg>
                <span className="hidden sm:inline">Scan</span>
              </button>
              {(!verticalPack || verticalPack === 'datacenter') && (
                <button
                  onClick={() => setShowPowerEfficiencyModal(true)}
                  className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition flex items-center gap-2"
                  title="Analyze power efficiency of devices in storage"
                >
                  <span>⚡</span>
                  <span className="hidden sm:inline">Efficiency</span>
                </button>
              )}
            </>
          )}
          {!isAuthenticated && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">Login to make changes</p>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <AssetFilters
        search={search}
        onSearchChange={setSearch}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        assetTypes={assetTypes}
        topAssetTypeFilters={topAssetTypeFilters}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        hideStorageBoxes={hideStorageBoxes}
        onHideStorageBoxesChange={setHideStorageBoxes}
        totalCount={assets.length}
        t={t}
        getAssetTypeDisplayName={getAssetTypeDisplayName}
      />

      {/* Assets Table */}
      <AssetTable
        loading={loading}
        filteredAssets={filteredAssets}
        groupedAssets={groupedAssets}
        selectedAssets={selectedAssets}
        expandedGroups={expandedGroups}
        assets={assets}
        isAuthenticated={isAuthenticated}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        handleSelectAll={handleSelectAll}
        handleSort={handleSort}
        handleSelectAsset={handleSelectAsset}
        handleSelectGroup={handleSelectGroup}
        openEditModal={openEditModal}
        handleDelete={handleDelete}
        setPrintingAsset={setPrintingAsset}
        setShowLabelPrint={setShowLabelPrint}
        toggleGroup={toggleGroup}
        getSortIndicator={getSortIndicator}
        shouldShowColumn={shouldShowColumn}
        getStatusBadge={getStatusBadge}
        getLocationDisplay={getLocationDisplay}
        getAssetTypeDisplayName={getAssetTypeDisplayName}
        getDatacenterName={getDatacenterName}
        getAssetDatacenterId={getAssetDatacenterId}
        t={t}
      />

      {/* Add/Edit Modal */}
      <AssetFormModal
        showModal={showModal}
        editingAsset={editingAsset}
        formData={formData}
        setFormData={setFormData}
        error={error}
        saving={saving}
        uploadedImageUrl={uploadedImageUrl}
        setUploadedImageUrl={setUploadedImageUrl}
        useManualSerial={useManualSerial}
        setUseManualSerial={setUseManualSerial}
        portTemplates={portTemplates}
        selectedTemplateId={selectedTemplateId}
        setSelectedTemplateId={setSelectedTemplateId}
        overwritePorts={overwritePorts}
        setOverwritePorts={setOverwritePorts}
        skuLookupLoading={skuLookupLoading}
        skuLookupError={skuLookupError}
        skuAutocompleteSuggestions={skuAutocompleteSuggestions}
        showSkuAutocomplete={showSkuAutocomplete}
        setShowSkuAutocomplete={setShowSkuAutocomplete}
        assetTypes={assetTypes}
        datacenters={datacenters}
        racks={racks}
        rooms={rooms}
        storageContainers={storageContainers}
        assets={assets}
        closeModal={closeModal}
        handleSubmit={handleSubmit}
        handleInputChange={handleInputChange}
        handleOCRComplete={handleOCRComplete}
        handleOCRClear={handleOCRClear}
        handleSKULookup={handleSKULookup}
        fetchSkuAutocomplete={fetchSkuAutocomplete}
        handleSkuAutocompleteSelect={handleSkuAutocompleteSelect}
        shouldShowField={shouldShowField}
        t={t}
        verticalPack={verticalPack}
        hasFeature={hasFeature}
      />

      {/* Bulk Edit Modal */}
      {/* Bulk Edit Modal */}
      <AssetBulkEditModal
        showBulkEditModal={showBulkEditModal}
        closeBulkEditModal={closeBulkEditModal}
        selectedAssets={selectedAssets}
        error={error}
        saving={saving}
        bulkEditData={bulkEditData}
        setBulkEditData={setBulkEditData}
        bulkEditAssetTypeInfo={bulkEditAssetTypeInfo}
        assetTypes={assetTypes}
        datacenters={datacenters}
        racks={racks}
        rooms={rooms}
        storageContainers={storageContainers}
        portTemplates={portTemplates}
        selectedTemplateId={selectedTemplateId}
        setSelectedTemplateId={setSelectedTemplateId}
        overwritePorts={overwritePorts}
        setOverwritePorts={setOverwritePorts}
        handleBulkEdit={handleBulkEdit}
        t={t}
      />
      <BarcodeScanner
        isOpen={showBarcodeScanner}
        onClose={() => setShowBarcodeScanner(false)}
        onScanSuccess={handleBarcodeScan}
      />

      {/* Label Print Modal */}
      {
        printingAsset && (
          <LabelPrintModal
            isOpen={showLabelPrint}
            onClose={() => {
              setShowLabelPrint(false);
              setPrintingAsset(null);
            }}
            item={printingAsset}
            itemType="asset"
          />
        )
      }

      {/* SKU Match Modal - Shows when FS.com product detected */}
      {
        showSKUMatchModal && (
          <SKUMatchModal
            isOpen={showSKUMatchModal}
            onClose={() => setShowSKUMatchModal(false)}
            onSelectSKU={handleSKUSelected}
            detectedText={ocrDetectedText}
            imageUrl={uploadedImageUrl || undefined}
          />
        )
      }

      {/* Power Efficiency Advisor Modal */}
      <PowerEfficiencyModal
        isOpen={showPowerEfficiencyModal}
        onClose={() => setShowPowerEfficiencyModal(false)}
        onSelectAsset={(assetId) => navigate(`/assets/${assetId}`)}
      />
    </div >
  );
};

export default Assets;
