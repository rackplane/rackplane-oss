// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import LabelPrintModal from '../components/LabelPrintModal';
import AssetConnections from '../components/AssetConnections';
import { StorageBoxItems } from '../components/StorageBoxItems';
import PortList from '../components/PortList';
import TemplateSelector from '../components/TemplateSelector';
import PortCreateModal from '../components/PortCreateModal';
import { NetworkPort } from '../components/PortList';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import logger from '../utils/logger';
import { formatStatus } from '../utils/formatStatus';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  sku?: string;
  status: string;
  on_loan?: boolean;
  loan_direction?: string;
  loan_party?: string;
  loan_source?: string;
  hostname?: string;
  primary_ip?: string;
  management_ip?: string;
  height_u?: number;
  power_consumption_watts?: number;
  description?: string;
  notes?: string;
  datacenter_id?: number;
  rack_id?: number;
  rack_position_start?: number;  // Starting U position (bottom)
  rack_position_end?: number;      // Ending U position (top)
  storage_container_id?: number;
  storage_location?: string;
  container_id?: number;  // Asset inside another asset (box/bin)
  min_stock_threshold?: number;  // Minimum stock level for storage boxes
  purchase_cost?: number;
  purchase_date?: string;
  currency?: string;
  supplier?: string;
  po_number?: string;
  warranty_start_date?: string;
  warranty_end_date?: string;
  custom_fields?: {
    [key: string]: any;
  };
  // Management interface tracking
  has_console?: boolean;
  has_ipmi?: boolean;
  has_pdu?: boolean;
  console_link?: string;
  ipmi_link?: string;
  pdu_link?: string;
  // Management interface credentials
  ipmi_username?: string;
  ipmi_password?: string;
  console_username?: string;
  console_password?: string;
  // Images
  photo_urls?: string[];
  created_at?: string;
  updated_at?: string;
}

interface AssetType {
  id: number;
  name: string;
  display_name: string;
  features?: Record<string, any>;
}

interface Datacenter {
  id: number;
  name: string;
  code: string;
}

interface Rack {
  id: number;
  name: string;
}

interface Room {
  id: number;
  name: string;
  code: string;
}

interface StorageContainer {
  id: number;
  name: string;
  container_type: string;
  datacenter_id?: number;
  room_id?: number;
  location?: string;
}

// QR Code Image Component with Authentication
const QRCodeImage: React.FC<{ assetId: number; assetTag: string }> = ({ assetId, assetTag }) => {
  const { token } = useAuth();
  const { t } = useWhiteLabel();
  const [imageUrl, setImageUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const downloadLinkRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    const fetchQRCode = async () => {
      if (!token) {
        setError(true);
        setLoading(false);
        return;
      }

      try {
        const response = await axios.get(
          `${API_URL}/api/v1/barcodes/generate/${assetId}`,
          {
            responseType: 'blob',
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        const blob = new Blob([response.data], { type: 'image/png' });
        const url = URL.createObjectURL(blob);
        setImageUrl(url);
        setLoading(false);
      } catch (err) {
        logger.error('Error fetching QR code:', err);
        setError(true);
        setLoading(false);
      }
    };

    fetchQRCode();

    // Cleanup blob URL on unmount
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [assetId, token]);

  const handleDownload = async () => {
    if (!token || !imageUrl) return;

    try {
      const response = await axios.get(
        `${API_URL}/api/v1/barcodes/generate/${assetId}`,
        {
          responseType: 'blob',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const blob = new Blob([response.data], { type: 'image/png' });
      const url = URL.createObjectURL(blob);
      if (downloadLinkRef.current) {
        downloadLinkRef.current.href = url;
        downloadLinkRef.current.download = `qr-${assetTag}.png`;
        downloadLinkRef.current.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      logger.error('Error downloading QR code:', err);
      alert('Failed to download QR code');
    }
  };

  const handlePrint = async () => {
    if (!token) return;

    try {
      const response = await axios.get(
        `${API_URL}/api/v1/barcodes/generate/${assetId}`,
        {
          responseType: 'blob',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const blob = new Blob([response.data], { type: 'image/png' });
      const url = URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
          URL.revokeObjectURL(url);
        };
      }
    } catch (err) {
      logger.error('Error printing QR code:', err);
      alert('Failed to print QR code');
    }
  };

  if (loading) {
    return <div className="w-48 h-48 flex items-center justify-center text-gray-500 dark:text-gray-400">Loading QR Code...</div>;
  }

  if (error) {
    return (
      <div className="w-48 h-48 flex items-center justify-center text-red-500">
        Failed to load QR Code
      </div>
    );
  }

  return (
    <>
      <img
        src={imageUrl}
        alt={`${t('item')} QR Code`}
        className="w-48 h-48"
      />
      <div className="flex gap-2 justify-center mt-4">
        <a
          ref={downloadLinkRef}
          onClick={handleDownload}
          className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm cursor-pointer"
        >
          Download
        </a>
        <button
          onClick={handlePrint}
          className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
        >
          Print
        </button>
      </div>
    </>
  );
};

const AssetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t, verticalPack } = useWhiteLabel();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [racks, setRacks] = useState<Rack[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [storageContainers, setStorageContainers] = useState<StorageContainer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editingBasicInfo, setEditingBasicInfo] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state for editing management interfaces
  const [formData, setFormData] = useState({
    has_console: false,
    has_ipmi: false,
    has_pdu: false,
    console_link: '',
    ipmi_link: '',
    pdu_link: '',
    ipmi_username: '',
    ipmi_password: '',
    console_username: '',
    console_password: '',
  });

  // Form state for editing basic asset info (serial number, etc.)
  const [basicInfoData, setBasicInfoData] = useState({
    serial_number: '',
    manufacturer: '',
    model: '',
    description: '',
    notes: '',
  });

  // Image upload state
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageUrl, setImageUrl] = useState('');

  // Label print state
  const [showLabelPrint, setShowLabelPrint] = useState(false);

  // Clone modal state
  const [showCloneModal, setShowCloneModal] = useState(false);
  const [cloneQuantity, setCloneQuantity] = useState(1);
  const [clonePrefix, setClonePrefix] = useState('');
  const [cloning, setCloning] = useState(false);

  // Port management state
  const [showPortCreate, setShowPortCreate] = useState(false);
  const [editingPort, setEditingPort] = useState<NetworkPort | null>(null);
  const [portRefreshKey, setPortRefreshKey] = useState(0);

  // Convert to Contract state
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [converting, setConverting] = useState(false);

  /**
   * Memoized lookup for migrated storage container.
   * If this asset's asset_tag matches a StorageContainer name, it was migrated.
   * This replaces the inline IIFE in the render for better readability.
   */
  const migratedStorageContainer = useMemo(() => {
    if (!asset) return null;
    return storageContainers.find(c => c.name === asset.asset_tag) || null;
  }, [asset, storageContainers]);


  useEffect(() => {
    if (id) {
      logger.debug('AssetDetail: useEffect triggered, id:', id, 'current location:', window.location.pathname);
      // Check if we're actually on the asset page (not being redirected)
      if (window.location.pathname !== `/assets/${id}`) {
        logger.warn('AssetDetail: Path mismatch! Expected /assets/' + id + ' but got ' + window.location.pathname);
      }
      fetchAsset();
      fetchAssetTypes();
      fetchDatacenters();
      fetchRacks();
      fetchRooms();
      fetchStorageContainers();
    }
  }, [id]);

  // Monitor for unexpected navigation away from this page
  useEffect(() => {
    const checkLocation = () => {
      if (id && window.location.pathname !== `/assets/${id}` && !window.location.pathname.startsWith('/assets/')) {
        logger.warn('AssetDetail: Unexpected navigation detected! Current path:', window.location.pathname, 'Expected: /assets/' + id);
      }
    };

    // Check immediately and after a short delay
    checkLocation();
    const timeout = setTimeout(checkLocation, 100);

    return () => clearTimeout(timeout);
  }, [id]);

  // Log when asset is set and check for rack_id
  useEffect(() => {
    if (asset) {
      logger.debug('AssetDetail: Asset state updated:', asset.asset_tag, 'rack_id:', asset.rack_id, 'current path:', window.location.pathname);
      // Check if we're still on the asset page
      if (window.location.pathname !== `/assets/${asset.id}`) {
        logger.warn('AssetDetail: Navigation away from asset page detected! Path:', window.location.pathname, 'Asset ID:', asset.id);
      }
    }
  }, [asset]);

  const fetchAsset = async () => {
    try {
      setLoading(true);
      logger.debug('AssetDetail: fetchAsset called for id:', id);
      const response = await axios.get(`${API_URL}/api/v1/assets/${id}`);
      logger.debug('AssetDetail: Asset fetched:', response.data.asset_tag, 'rack_id:', response.data.rack_id);
      setAsset(response.data);

      // Initialize form data
      setFormData({
        has_console: response.data.has_console || false,
        has_ipmi: response.data.has_ipmi || false,
        has_pdu: response.data.has_pdu || false,
        console_link: response.data.console_link || '',
        ipmi_link: response.data.ipmi_link || '',
        pdu_link: response.data.pdu_link || '',
        ipmi_username: response.data.ipmi_username || '',
        ipmi_password: response.data.ipmi_password || '',
        console_username: response.data.console_username || '',
        console_password: response.data.console_password || '',
      });

      // Initialize basic info data
      setBasicInfoData({
        serial_number: response.data.serial_number || '',
        manufacturer: response.data.manufacturer || '',
        model: response.data.model || '',
        description: response.data.description || '',
        notes: response.data.notes || '',
      });
    } catch (err: any) {
      logger.error('Failed to fetch asset:', err);
      setError('Failed to load asset details');
    } finally {
      setLoading(false);
    }
  };

  const fetchAssetTypes = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/asset-types/`);
      setAssetTypes(response.data || []);
    } catch (error) {
      logger.error('Error fetching asset types:', error);
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

  const fetchRacks = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`);
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching racks:', error);
    }
  };

  const fetchStorageContainers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/`);
      setStorageContainers(response.data || []);
    } catch (error) {
      logger.error('Error fetching storage containers:', error);
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

  const handleCheckboxChange = (field: 'has_console' | 'has_ipmi' | 'has_pdu') => {
    setFormData(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const handleLinkChange = (field: 'console_link' | 'ipmi_link' | 'pdu_link', value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCredentialChange = (field: 'ipmi_username' | 'ipmi_password' | 'console_username' | 'console_password', value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await axios.put(`${API_URL}/api/v1/assets/${id}`, {
        ...asset,
        ...formData
      });
      await fetchAsset();
      setEditing(false);
      alert('Management interfaces updated successfully!');
    } catch (err: any) {
      logger.error('Failed to update asset:', err);
      alert(`Failed to update ${t('item').toLowerCase()}: ` + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveBasicInfo = async () => {
    try {
      setSaving(true);
      await axios.put(`${API_URL}/api/v1/assets/${id}`, {
        ...asset,
        serial_number: basicInfoData.serial_number,
        manufacturer: basicInfoData.manufacturer,
        model: basicInfoData.model,
        description: basicInfoData.description,
        notes: basicInfoData.notes,
      });
      await fetchAsset();
      setEditingBasicInfo(false);
      await fetchAsset();
      setEditingBasicInfo(false);
      alert(`${t('item')} information updated successfully!`);
    } catch (err: any) {
      logger.error('Failed to update asset:', err);
      alert(`Failed to update ${t('item').toLowerCase()}: ` + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleAddImage = async () => {
    if (!imageUrl.trim()) {
      alert('Please enter an image URL');
      return;
    }

    try {
      setUploadingImage(true);
      const updatedPhotoUrls = [...(asset?.photo_urls || []), imageUrl];

      await axios.put(`${API_URL}/api/v1/assets/${id}`, {
        ...asset,
        photo_urls: updatedPhotoUrls
      });

      await fetchAsset();
      setImageUrl('');
      alert('Image added successfully!');
    } catch (err: any) {
      logger.error('Failed to add image:', err);
      alert('Failed to add image: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploadingImage(false);
    }
  };

  const handleRemoveImage = async (urlToRemove: string) => {
    if (!window.confirm('Are you sure you want to remove this image?')) {
      return;
    }

    try {
      const updatedPhotoUrls = (asset?.photo_urls || []).filter(url => url !== urlToRemove);

      await axios.put(`${API_URL}/api/v1/assets/${id}`, {
        ...asset,
        photo_urls: updatedPhotoUrls
      });

      await fetchAsset();
      alert('Image removed successfully!');
    } catch (err: any) {
      logger.error('Failed to remove image:', err);
      alert('Failed to remove image: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete this ${t('item').toLowerCase()}? This action cannot be undone.`)) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/assets/${id}`);
      alert(`${t('item')} deleted successfully!`);
      navigate('/assets');
    } catch (err: any) {
      logger.error('Failed to delete asset:', err);
      alert(`Failed to delete ${t('item').toLowerCase()}: ` + (err.response?.data?.detail || err.message));
    }
  };

  const handleClone = async () => {
    if (cloneQuantity < 1 || cloneQuantity > 100) {
      alert('Quantity must be between 1 and 100');
      return;
    }

    try {
      setCloning(true);
      const response = await axios.post(`${API_URL}/api/v1/assets/${id}/clone`, {
        quantity: cloneQuantity,
        prefix: clonePrefix || undefined
      });

      const result = response.data;
      alert(`Successfully created ${result.cloned_count} clone(s)!\n\nNew asset tags:\n${result.created_asset_tags.join('\n')}`);
      setShowCloneModal(false);
      setCloneQuantity(1);
      setClonePrefix('');

      // Navigate to first cloned asset
      if (result.created_asset_ids && result.created_asset_ids.length > 0) {
        navigate(`/assets/${result.created_asset_ids[0]}`);
      }
    } catch (err: any) {
      logger.error('Failed to clone asset:', err);
      alert(`Failed to clone ${t('item').toLowerCase()}: ` + (err.response?.data?.detail || err.message));
    } finally {
      setCloning(false);
    }
  };

  const handleConvertToContract = async () => {
    if (!window.confirm(
      `Convert this ${t('item').toLowerCase()} to a Service Contract?\n\n` +
      'This will:\n' +
      `• Create a new service contract with this ${t('item').toLowerCase()}'s info\n` +
      `• Delete the original ${t('item').toLowerCase()}\n\n` +
      'Continue?'
    )) {
      return;
    }

    try {
      setConverting(true);
      const response = await axios.post(`${API_URL}/api/v1/service-contracts/from-asset/${id}`, {
        contract_type: 'professional_services',
        delete_asset: true
      });

      const result = response.data;
      alert(`✅ ${result.message}\n\nNew contract ID: ${result.contract_id}`);

      // Navigate to the service contracts page
      navigate('/service-contracts');
    } catch (err: any) {
      logger.error('Failed to convert asset to contract:', err);
      alert('Failed to convert: ' + (err.response?.data?.detail || err.message));
    } finally {
      setConverting(false);
      setShowConvertModal(false);
    }
  };

  const getAssetTypeDisplayName = (assetTypeName: string): string => {
    const assetType = assetTypes.find(type => type.name === assetTypeName);
    return assetType?.display_name || assetTypeName;
  };

  const getDatacenterName = (datacenterId?: number): string => {
    if (!datacenterId) return '-';
    const datacenter = datacenters.find(dc => dc.id === datacenterId);
    return datacenter ? `${datacenter.name} (${datacenter.code})` : '-';
  };

  const getRackName = (rackId?: number): string => {
    if (!rackId) return '-';
    const rack = racks.find(r => r.id === rackId);
    return rack?.name || '-';
  };

  const getRoomName = (roomId?: number): string => {
    if (!roomId) return '-';
    const room = rooms.find(r => r.id === roomId);
    return room?.name || '-';
  };

  const extractRackFromLocation = (locationText: string, nameText: string): string | null => {
    // Check if location or name mentions a rack
    const combined = (locationText + ' ' + nameText).toLowerCase();
    if (!combined.includes('rack')) return null;

    // Try to extract rack code (e.g., "RACK-2", "RACK-3", "rack-8-31")
    const rackMatch = combined.match(/rack[-_]?([\d\.\-]+)/i);
    if (rackMatch) {
      const rackNumber = rackMatch[1].replace(/\./g, '-');
      return rackNumber.includes('-') ? `RACK-${rackNumber.toUpperCase()}` : `RACK-${rackNumber.toUpperCase()}`;
    }
    return null;
  };

  const getLocationLabel = (): string => {
    // If asset is directly in a rack, show "Rack"
    if (asset?.rack_id) {
      return t('bin');
    }
    // If asset is in a storage container, check where the container is
    if (asset?.storage_container_id) {
      const container = storageContainers.find(c => c.id === asset.storage_container_id);
      if (!container) return t('bin');

      // Check if container location/name mentions a rack
      const locationText = (container.location || '').toLowerCase();
      const nameText = (container.name || '').toLowerCase();
      const rackCode = extractRackFromLocation(container.location || '', container.name || '');

      if (rackCode) {
        // Container is on a rack
        return t('bin');
      }

      // Container is in a room/cage
      if (container.room_id) {
        const room = rooms.find(r => r.id === container.room_id);
        // Check if room name contains "Cage" to determine label
        if (room?.name.toLowerCase().includes('cage')) {
          return 'Cage';
        }
        return 'Room';
      }
    }
    // Default to "Rack" if no specific location
    return t('bin');
  };

  const getLocationValue = (): string => {
    // If asset is directly in a rack, show rack name
    if (asset?.rack_id) {
      return getRackName(asset.rack_id);
    }
    // If asset is in a storage container, check where the container is
    if (asset?.storage_container_id) {
      const container = storageContainers.find(c => c.id === asset.storage_container_id);
      if (!container) return '-';

      // Check if container location/name mentions a rack
      const rackCode = extractRackFromLocation(container.location || '', container.name || '');
      if (rackCode) {
        // Container is on a rack - show the rack code
        return rackCode;
      }

      // Container is in a room/cage - show the room/cage name
      if (container.room_id) {
        return getRoomName(container.room_id);
      }
    }
    return '-';
  };

  const getStorageContainerName = (containerId?: number): string => {
    if (!containerId) return '-';
    const container = storageContainers.find(c => c.id === containerId);
    return container ? `${container.name} (${container.container_type})` : '-';
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

  const isSwitch = asset?.asset_type.toLowerCase().includes('switch');
  const isServer = asset?.asset_type.toLowerCase().includes('server');

  // Check if this asset type supports networking features (ports, cables, management interfaces)
  const currentAssetType = assetTypes.find(t => t.name === asset?.asset_type);
  const isNetworkable = currentAssetType?.features?.networkable ?? false;

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500 dark:text-gray-400">Loading {t('item').toLowerCase()} details...</div>
      </div>
    );
  }

  if (error || !asset) {
    return (
      <div>
        <Link to="/assets" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to {t('items')}
        </Link>
        <div className="card">
          <div className="text-red-600">{error || `${t('item')} not found`}</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link to="/assets" className="text-blue-600 hover:text-blue-800 mb-2 inline-block">
            ← Back to {t('items')}
          </Link>
          <h1 className="text-3xl font-bold text-primary">
            {asset.hostname || asset.asset_tag}
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {getAssetTypeDisplayName(asset.asset_type)} - {asset.manufacturer} {asset.model}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/assets?edit=${id}`)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            title={`Edit this ${t('item').toLowerCase()}`}
          >
            ✏️ Edit {t('item')}
          </button>
          <button
            onClick={() => setShowLabelPrint(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            title="Print label for Brother PT-E550W"
          >
            🏷️ Print Label
          </button>
          <button
            onClick={() => navigate(`/assets`)}
            className="btn-secondary"
          >
            View All {t('items')}
          </button>
          <button
            onClick={() => setShowCloneModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            title={`Clone this ${t('item').toLowerCase()}`}
          >
            📋 Clone
          </button>
          <button
            onClick={handleConvertToContract}
            disabled={converting}
            className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
            title={`Convert this ${t('item').toLowerCase()} to a service contract`}
          >
            {converting ? '⏳ Converting...' : '📝 To Contract'}
          </button>
          <button
            onClick={handleDelete}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Delete {t('item')}
          </button>
        </div>
      </div>

      {/* Clone Modal */}
      {showCloneModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-primary mb-4">Clone {t('item')}</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Create duplicates of <strong>{asset.asset_tag}</strong>
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">
                  Quantity (1-100)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={cloneQuantity}
                  onChange={(e) => setCloneQuantity(parseInt(e.target.value) || 1)}
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">
                  {t('item')} Tag Prefix (optional)
                </label>
                <input
                  type="text"
                  value={clonePrefix}
                  onChange={(e) => setClonePrefix(e.target.value)}
                  className="input w-full"
                  placeholder={`Leave empty for ${asset.asset_tag}-CLONE-1, etc.`}
                />
              </div>

              <div className="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 p-3 rounded">
                <strong>Preview:</strong> New {t('items').toLowerCase()} will be tagged as:
                <br />
                {clonePrefix
                  ? `${clonePrefix}-XXXXXXXX (UUID suffix)`
                  : `${asset.asset_tag}-CLONE-1, ${asset.asset_tag}-CLONE-2, ...`
                }
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowCloneModal(false);
                  setCloneQuantity(1);
                  setClonePrefix('');
                }}
                className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
                disabled={cloning}
              >
                Cancel
              </button>
              <button
                onClick={handleClone}
                disabled={cloning}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {cloning ? 'Cloning...' : `Create ${cloneQuantity} Clone${cloneQuantity > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Information */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Card */}
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">{t('item')} Overview</h2>

            {/* Primary Image Display */}
            {asset.photo_urls && asset.photo_urls.length > 0 && (
              <div className="mb-6 border border-gray-200 rounded-lg overflow-hidden">
                <img
                  src={asset.photo_urls[0]}
                  alt="Asset Primary"
                  className="w-full h-64 object-contain bg-image-container"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'https://via.placeholder.com/800x400?text=Image+Not+Available';
                  }}
                />
                <div className="px-3 py-2 bg-subtle-card text-xs text-gray-500 dark:text-gray-400">
                  Primary Image {asset.photo_urls.length > 1 && `(${asset.photo_urls.length} total images)`}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('item')} Tag</label>
                <p className="text-primary font-medium">{asset.asset_tag}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Serial Number</label>
                {editingBasicInfo ? (
                  <input
                    type="text"
                    value={basicInfoData.serial_number}
                    onChange={(e) => setBasicInfoData({ ...basicInfoData, serial_number: e.target.value })}
                    className="input w-full mt-1"
                    placeholder="Enter serial number"
                  />
                ) : (
                  <p className="text-primary">{asset.serial_number}</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</label>
                <p className="text-primary">{getAssetTypeDisplayName(asset.asset_type)}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</label>
                <span className={getStatusBadge(asset.status)}>{formatStatus(asset.status)}</span>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Manufacturer</label>
                {editingBasicInfo ? (
                  <input
                    type="text"
                    value={basicInfoData.manufacturer}
                    onChange={(e) => setBasicInfoData({ ...basicInfoData, manufacturer: e.target.value })}
                    className="input w-full mt-1"
                    placeholder="Enter manufacturer"
                  />
                ) : (
                  <p className="text-primary">{asset.manufacturer || '-'}</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Model</label>
                {editingBasicInfo ? (
                  <input
                    type="text"
                    value={basicInfoData.model}
                    onChange={(e) => setBasicInfoData({ ...basicInfoData, model: e.target.value })}
                    className="input w-full mt-1"
                    placeholder="Enter model"
                  />
                ) : (
                  <p className="text-primary">{asset.model || '-'}</p>
                )}
              </div>
              {asset.sku && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">SKU</label>
                  <p className="text-primary">{asset.sku}</p>
                </div>
              )}
              {asset.hostname && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Hostname</label>
                  <p className="text-primary">{asset.hostname}</p>
                </div>
              )}
              {asset.primary_ip && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Primary IP</label>
                  <p className="text-primary">{asset.primary_ip}</p>
                </div>
              )}
              {asset.management_ip && (
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Management IP</label>
                  <p className="text-primary">{asset.management_ip}</p>
                </div>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Description</label>
              {editingBasicInfo ? (
                <textarea
                  value={basicInfoData.description}
                  onChange={(e) => setBasicInfoData({ ...basicInfoData, description: e.target.value })}
                  className="input w-full mt-1"
                  rows={3}
                  placeholder="Enter description"
                />
              ) : (
                <p className="text-primary mt-1">{asset.description || '-'}</p>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Notes</label>
              {editingBasicInfo ? (
                <textarea
                  value={basicInfoData.notes}
                  onChange={(e) => setBasicInfoData({ ...basicInfoData, notes: e.target.value })}
                  className="input w-full mt-1"
                  rows={3}
                  placeholder="Enter notes"
                />
              ) : (
                <p className="text-primary mt-1">{asset.notes || '-'}</p>
              )}
            </div>
          </div>

          {/* Management Interfaces Card - Networkable Assets Only */}
          {isNetworkable && (
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-primary">Management Interfaces</h2>
                {!editing ? (
                  <button
                    onClick={() => setEditing(true)}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Edit
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        setEditing(false);
                        setFormData({
                          has_console: asset.has_console || false,
                          has_ipmi: asset.has_ipmi || false,
                          has_pdu: asset.has_pdu || false,
                          console_link: asset.console_link || '',
                          ipmi_link: asset.ipmi_link || '',
                          pdu_link: asset.pdu_link || '',
                          ipmi_username: asset.ipmi_username || '',
                          ipmi_password: asset.ipmi_password || '',
                          console_username: asset.console_username || '',
                          console_password: asset.console_password || '',
                        });
                      }}
                      className="px-3 py-1 bg-gray-400 text-white rounded hover:bg-gray-500 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                {/* Console Access (for switches) */}
                {isSwitch && (
                  <div className="bg-section-card">
                    <div className="flex items-center mb-3">
                      <input
                        type="checkbox"
                        id="has_console"
                        checked={formData.has_console}
                        onChange={() => handleCheckboxChange('has_console')}
                        disabled={!editing}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <label htmlFor="has_console" className="ml-2 text-sm font-medium text-primary">
                        Has Console Access
                      </label>
                    </div>
                    {formData.has_console && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-primary mb-2">
                            Console Link / Port
                          </label>
                          {editing ? (
                            <input
                              type="text"
                              value={formData.console_link}
                              onChange={(e) => handleLinkChange('console_link', e.target.value)}
                              className="input w-full"
                              placeholder="e.g., http://console.example.com/port/1 or Port 24"
                            />
                          ) : (
                            <p className="text-primary">
                              {formData.console_link || '-'}
                            </p>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-sm font-medium text-primary mb-2">
                              Username
                            </label>
                            {editing ? (
                              <input
                                type="text"
                                value={formData.console_username}
                                onChange={(e) => handleCredentialChange('console_username', e.target.value)}
                                className="input w-full"
                                placeholder="Username"
                              />
                            ) : (
                              <p className="text-primary font-mono text-sm">
                                {formData.console_username || '-'}
                              </p>
                            )}
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-primary mb-2">
                              Password
                            </label>
                            {editing ? (
                              <input
                                type="text"
                                value={formData.console_password}
                                onChange={(e) => handleCredentialChange('console_password', e.target.value)}
                                className="input w-full"
                                placeholder="Password"
                              />
                            ) : (
                              <p className="text-primary font-mono text-sm">
                                {formData.console_password || '-'}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* IPMI Access (for servers) */}
                {isServer && (
                  <div className="bg-section-card">
                    <div className="flex items-center mb-3">
                      <input
                        type="checkbox"
                        id="has_ipmi"
                        checked={formData.has_ipmi}
                        onChange={() => handleCheckboxChange('has_ipmi')}
                        disabled={!editing}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <label htmlFor="has_ipmi" className="ml-2 text-sm font-medium text-primary">
                        Has IPMI / BMC Access
                      </label>
                    </div>
                    {formData.has_ipmi && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-primary mb-2">
                            IPMI Link
                          </label>
                          {editing ? (
                            <input
                              type="text"
                              value={formData.ipmi_link}
                              onChange={(e) => handleLinkChange('ipmi_link', e.target.value)}
                              className="input w-full"
                              placeholder="e.g., https://10.0.1.100"
                            />
                          ) : (
                            <p className="text-primary">
                              {formData.ipmi_link ? (
                                <a
                                  href={formData.ipmi_link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800"
                                >
                                  {formData.ipmi_link}
                                </a>
                              ) : '-'}
                            </p>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-sm font-medium text-primary mb-2">
                              Username
                            </label>
                            {editing ? (
                              <input
                                type="text"
                                value={formData.ipmi_username}
                                onChange={(e) => handleCredentialChange('ipmi_username', e.target.value)}
                                className="input w-full"
                                placeholder="Username"
                              />
                            ) : (
                              <p className="text-primary font-mono text-sm">
                                {formData.ipmi_username || '-'}
                              </p>
                            )}
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-primary mb-2">
                              Password
                            </label>
                            {editing ? (
                              <input
                                type="text"
                                value={formData.ipmi_password}
                                onChange={(e) => handleCredentialChange('ipmi_password', e.target.value)}
                                className="input w-full"
                                placeholder="Password"
                              />
                            ) : (
                              <p className="text-primary font-mono text-sm">
                                {formData.ipmi_password || '-'}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* PDU Connection (for both) */}
                <div className="bg-section-card">
                  <div className="flex items-center mb-3">
                    <input
                      type="checkbox"
                      id="has_pdu"
                      checked={formData.has_pdu}
                      onChange={() => handleCheckboxChange('has_pdu')}
                      disabled={!editing}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <label htmlFor="has_pdu" className="ml-2 text-sm font-medium text-primary">
                      Connected to PDU
                    </label>
                  </div>
                  {formData.has_pdu && (
                    <div>
                      <label className="block text-sm font-medium text-primary mb-2">
                        PDU Link / Port
                      </label>
                      {editing ? (
                        <input
                          type="text"
                          value={formData.pdu_link}
                          onChange={(e) => handleLinkChange('pdu_link', e.target.value)}
                          className="input w-full"
                          placeholder="e.g., http://pdu.example.com/outlet/5 or PDU-A Port 12"
                        />
                      ) : (
                        <p className="text-primary">
                          {formData.pdu_link || '-'}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Cable Connections - Networkable Assets Only */}
          {isNetworkable && (
            <div className="card">
              <AssetConnections assetId={parseInt(id || '0')} />
            </div>
          )}

          {/* Network Ports - Networkable Assets Only */}
          {isNetworkable && (
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-primary">Network Ports</h2>
                <button
                  onClick={() => setShowPortCreate(true)}
                  className="btn-primary text-sm"
                >
                  + Add Port
                </button>
              </div>
              <PortList
                key={portRefreshKey}
                assetId={parseInt(id || '0')}
                onRefresh={() => setPortRefreshKey((k: number) => k + 1)}
                onEdit={(port: NetworkPort) => {
                  setEditingPort(port);
                  setShowPortCreate(true);
                }}
              />
              <div className="mt-4">
                <TemplateSelector
                  assetId={parseInt(id || '0')}
                  onApply={() => setPortRefreshKey(k => k + 1)}
                />
              </div>
            </div>
          )}

          {/* Storage Box Information - Only show if NOT migrated to StorageContainer */}
          {/* Case 1: Migrated to StorageContainer - show migration message */}
          {migratedStorageContainer && (
            <div className="card bg-yellow-50 border border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-700">
              <h2 className="text-xl font-bold text-primary mb-4">⚠️ Migrated to Storage Container</h2>
              <div className="mb-4">
                <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                  This asset was migrated from the old storage box system to the new Storage Container system.
                  The storage box functionality is no longer available. Please use the Storage Container instead.
                </p>
                <Link
                  to={`/storage-containers/${migratedStorageContainer.id}`}
                  className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  View Storage Container: {migratedStorageContainer.name} →
                </Link>
              </div>
            </div>
          )}

          {/* Case 2: Legacy storage box - not migrated but has min_stock_threshold */}
          {!migratedStorageContainer && asset.min_stock_threshold != null && asset.min_stock_threshold > 0 && (
            <div className="card">
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 dark:bg-blue-900/20 dark:border-blue-700 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  <strong>Legacy Storage Box:</strong> This asset is using the old storage box system.
                  Consider migrating it to a Storage Container for better functionality.
                </p>
              </div>
              <h2 className="text-xl font-bold text-primary mb-4">{t('container')} Contents</h2>
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-primary">Minimum Stock Level:</span>
                  <span className="text-lg font-bold text-blue-600">{asset.min_stock_threshold}</span>
                </div>
                <StorageBoxItems containerId={asset.id} />
              </div>
            </div>
          )}

          {/* Item Location - If inside a storage box */}
          {asset.container_id && (
            <div className="card bg-blue-50 border border-blue-200">
              <h2 className="text-xl font-bold text-primary mb-4">{t('storage')} {t('location')}</h2>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-primary">Inside {t('container')}:</span>
                <Link
                  to={`/assets/${asset.container_id}`}
                  className="font-semibold text-blue-600 hover:underline"
                >
                  View {t('container')} →
                </Link>
              </div>
              <p className="text-xs text-secondary mt-2">
                This {t('item').toLowerCase()} is stored inside another {t('item').toLowerCase()} ({t('container').toLowerCase()}). Click the link above to view the {t('container').toLowerCase()} details.
              </p>
            </div>
          )}

          {/* Location Information */}
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">{t('location')}</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-secondary">{t('location')}</label>
                <p className="text-primary">
                  {getDatacenterName(
                    asset.datacenter_id ||
                    (asset.storage_container_id ? storageContainers.find(c => c.id === asset.storage_container_id)?.datacenter_id : undefined)
                  )}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-secondary">{getLocationLabel()}</label>
                {asset?.rack_id ? (
                  <div>
                    <Link
                      to={`/racks/${asset.rack_id}`}
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline"
                      tabIndex={-1}
                      onClick={(e) => {
                        logger.debug('AssetDetail: Rack link clicked, navigating to /racks/' + asset.rack_id);
                        // Allow normal navigation - don't prevent default
                      }}
                      onFocus={(e) => {
                        logger.debug('AssetDetail: Rack link received focus');
                      }}
                    >
                      {getRackName(asset.rack_id)}
                    </Link>
                    {asset.rack_position_start && (
                      <p className="text-primary mt-1">
                        Unit Position: U{asset.rack_position_start}
                        {asset.rack_position_end && asset.rack_position_end !== asset.rack_position_start
                          ? `-${asset.rack_position_end}`
                          : ''}
                      </p>
                    )}
                    {!asset.rack_position_start && (
                      <p className="text-secondary text-sm mt-1 italic">Unit position not set</p>
                    )}
                  </div>
                ) : (
                  <p className="text-primary">{getLocationValue()}</p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-secondary">{t('container')}</label>
                {asset.storage_container_id ? (
                  <Link
                    to={`/storage-containers/${asset.storage_container_id}`}
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline"
                  >
                    {getStorageContainerName(asset.storage_container_id)}
                  </Link>
                ) : (
                  <p className="text-primary">{getStorageContainerName(asset.storage_container_id)}</p>
                )}
              </div>
              {asset.storage_location && (
                <div>
                  <label className="text-sm font-medium text-secondary">Storage Location (Legacy)</label>
                  <p className="text-primary">{asset.storage_location}</p>
                </div>
              )}
            </div>
          </div>

          {/* Physical Specifications */}
          {(asset.height_u || asset.power_consumption_watts) && (
            <div className="card">
              <h2 className="text-xl font-bold text-primary mb-4">Physical Specifications</h2>
              <div className="grid grid-cols-2 gap-4">
                {asset.height_u && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Height (U)</label>
                    <p className="text-primary">{asset.height_u}U</p>
                  </div>
                )}
                {asset.power_consumption_watts && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Power Consumption</label>
                    <p className="text-primary">{asset.power_consumption_watts}W</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Financial Information */}
          {(asset.purchase_cost || asset.supplier || asset.warranty_start_date || asset.warranty_end_date) && (
            <div className="card">
              <h2 className="text-xl font-bold text-primary mb-4">Financial Information</h2>
              <div className="grid grid-cols-2 gap-4">
                {asset.purchase_cost && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Purchase Cost</label>
                    <p className="text-primary">
                      {asset.currency || 'USD'} {asset.purchase_cost.toFixed(2)}
                    </p>
                  </div>
                )}
                {asset.purchase_date && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Purchase Date</label>
                    <p className="text-primary">
                      {new Date(asset.purchase_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {asset.warranty_start_date && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Warranty Start Date</label>
                    <p className="text-primary">
                      {new Date(asset.warranty_start_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {asset.warranty_end_date && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Warranty Expiration Date</label>
                    <p className="text-primary">
                      {new Date(asset.warranty_end_date).toLocaleDateString()}
                      {new Date(asset.warranty_end_date) < new Date() && (
                        <span className="ml-2 text-red-600 dark:text-red-400 font-semibold">(Expired)</span>
                      )}
                      {new Date(asset.warranty_end_date) >= new Date() && new Date(asset.warranty_end_date) <= new Date(Date.now() + 90 * 24 * 60 * 60 * 1000) && (
                        <span className="ml-2 text-yellow-600 dark:text-yellow-400 font-semibold">(Expiring Soon)</span>
                      )}
                    </p>
                  </div>
                )}
                {asset.supplier && (
                  <div>
                    <label className="text-sm font-medium text-secondary">Supplier</label>
                    <p className="text-primary">{asset.supplier}</p>
                  </div>
                )}
                {asset.po_number && (
                  <div>
                    <label className="text-sm font-medium text-secondary">PO Number</label>
                    <p className="text-primary">{asset.po_number}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Images Card */}
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">Images</h2>

            {/* Add Image */}
            <div className="mb-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  className="input flex-1"
                  placeholder="Image URL"
                />
                <button
                  onClick={handleAddImage}
                  disabled={uploadingImage}
                  className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                >
                  {uploadingImage ? '...' : 'Add'}
                </button>
              </div>
              <p className="text-xs text-secondary mt-1">
                Enter a URL to an image (e.g., from Imgur, Google Drive, etc.)
              </p>
            </div>

            {/* Display Images */}
            {asset.photo_urls && asset.photo_urls.length > 0 ? (
              <div className="space-y-3">
                {asset.photo_urls.map((url, index) => (
                  <div key={index} className="relative group">
                    <img
                      src={url}
                      alt={`${t('item')} ${index + 1}`}
                      className="w-full h-48 object-cover rounded-lg"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'https://via.placeholder.com/400x300?text=Image+Not+Found';
                      }}
                    />
                    <button
                      onClick={() => handleRemoveImage(url)}
                      className="absolute top-2 right-2 bg-red-600 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-secondary text-center py-8">No images uploaded</p>
            )}
          </div>

          {/* Barcode/QR Code Card */}
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">QR Code</h2>
            <div className="text-center">
              <div className="bg-card border border-gray-200 rounded-lg p-4 inline-block mb-4">
                <QRCodeImage assetId={asset.id} assetTag={asset.asset_tag} />
              </div>
              <p className="text-xs text-secondary mt-3">
                Scan with the barcode scanner to quickly find this {t('item').toLowerCase()}
              </p>
            </div>
          </div>

          {/* Metadata Card */}
          <div className="card">
            <h2 className="text-xl font-bold text-primary mb-4">Metadata</h2>
            <div className="space-y-3">
              {asset.created_at && (
                <div>
                  <label className="text-sm font-medium text-secondary">Created</label>
                  <p className="text-primary text-sm">
                    {new Date(asset.created_at).toLocaleString()}
                  </p>
                </div>
              )}
              {asset.updated_at && (
                <div>
                  <label className="text-sm font-medium text-secondary">Last Updated</label>
                  <p className="text-primary text-sm">
                    {new Date(asset.updated_at).toLocaleString()}
                  </p>
                </div>
              )}
              {asset.on_loan && (
                <div>
                  <label className="text-sm font-medium text-secondary">Loan Status</label>
                  <p className="text-primary text-sm">
                    {asset.loan_direction === 'from_us'
                      ? `Loaned out${asset.loan_party ? ` to ${asset.loan_party}` : ''}`
                      : `On loan${asset.loan_party || asset.loan_source ? ` from ${asset.loan_party || asset.loan_source}` : ''}`
                    }
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Label Print Modal */}
      {asset && (
        <LabelPrintModal
          isOpen={showLabelPrint}
          onClose={() => setShowLabelPrint(false)}
          item={asset}
          itemType="asset"
        />
      )}

      {/* Port Create Modal */}
      <PortCreateModal
        assetId={parseInt(id || '0')}
        isOpen={showPortCreate}
        onClose={() => {
          setShowPortCreate(false);
          setEditingPort(null);
        }}
        onCreated={() => {
          setPortRefreshKey(k => k + 1);
          setEditingPort(null);
        }}
        editPort={editingPort}
      />
    </div>
  );
};

export default AssetDetail;
