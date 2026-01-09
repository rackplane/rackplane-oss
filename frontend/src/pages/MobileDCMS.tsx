// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { Html5QrcodeScanner, Html5QrcodeScanType } from 'html5-qrcode';
import LabelPrintModal from '../components/LabelPrintModal';
import ImageUploadOCR, { OCRResult } from '../components/ImageUploadOCR';
import logger from '../utils/logger';
import { formatStatus } from '../utils/formatStatus';
import { useCapabilities } from '../contexts/CapabilityContext';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  hostname?: string;
  status: string;
  custom_fields?: {
    quantity?: number;
    [key: string]: any;
  };
}

interface AssetType {
  id: number;
  name: string;
  display_name: string;
}

const MobileDCMS: React.FC = () => {
  const navigate = useNavigate();
  const { checkCapability, capabilities } = useCapabilities();
  const isPremium = capabilities?.build_mode === 'premium';
  const [currentView, setCurrentView] = useState<'home' | 'scan' | 'add' | 'inventory'>('home');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [filteredAssets, setFilteredAssets] = useState<Asset[]>([]);
  const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Scanner state
  const [scanning, setScanning] = useState(false);
  const [scanMode, setScanMode] = useState<'qr' | 'ocr'>('qr');
  const [scannedAsset, setScannedAsset] = useState<Asset | null>(null);
  const [scannerInstance, setScannerInstance] = useState<Html5QrcodeScanner | null>(null);

  // Add item state
  const [newItem, setNewItem] = useState({
    asset_tag: '',
    serial_number: '',
    asset_type: '',
    manufacturer: '',
    model: '',
    hostname: '',
    status: 'received',
    quantity: 1
  });

  // Label print state
  const [showLabelPrint, setShowLabelPrint] = useState(false);
  const [printingAsset, setPrintingAsset] = useState<Asset | null>(null);

  useEffect(() => {
    fetchAssets();
    fetchAssetTypes();
  }, []);

  useEffect(() => {
    // Filter assets whenever search term, status filter, or assets change
    const assetArray = Array.isArray(assets) ? assets : [];
    let filtered = assetArray;

    if (searchTerm) {
      filtered = filtered.filter(asset =>
        asset.asset_tag?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.serial_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.manufacturer?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (asset.hostname && asset.hostname.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(asset => asset.status === statusFilter);
    }

    setFilteredAssets(filtered);
    logger.debug('Filtered assets:', filtered.length, 'from total:', assetArray.length);
  }, [searchTerm, statusFilter, assets]);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const url = `${API_URL}/api/v1/assets/`;
      logger.debug('API_URL:', API_URL);
      logger.debug('Fetching from:', url);
      const response = await axios.get(url);

      // Handle paginated response format: {total, skip, limit, assets: [...]}
      // Or direct array format: [...]
      let assetData: Asset[];
      if (response.data.assets && Array.isArray(response.data.assets)) {
        // Paginated response
        assetData = response.data.assets;
        logger.debug(`Fetched ${assetData.length} of ${response.data.total} total assets`);
      } else if (Array.isArray(response.data)) {
        // Direct array response
        assetData = response.data;
        logger.debug('Fetched assets:', assetData.length, 'items');
      } else {
        assetData = [];
        logger.warn('Unexpected response format:', response.data);
      }

      logger.debug('Response data:', response.data);
      setAssets(assetData);
      setLoading(false);
    } catch (err: any) {
      logger.error('Failed to fetch assets:', err);
      logger.error('Error details:', err.response?.status, err.response?.data);
      logger.error('Full error:', err.message);
      setError('Failed to fetch assets');
      setAssets([]); // Ensure assets is always an array
      setLoading(false);
    }
  };

  const fetchAssetTypes = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/asset-types/`);
      setAssetTypes(response.data);
    } catch (err) {
      logger.error('Failed to fetch asset types:', err);
    }
  };

  const handleOCRComplete = (ocrResult: OCRResult) => {
    const { asset_tag, serial_number } = ocrResult.parsed_data;
    let foundAsset: Asset | undefined;

    if (asset_tag) {
      foundAsset = assets.find(a => a.asset_tag.toLowerCase() === asset_tag.toLowerCase());
    }
    if (!foundAsset && serial_number) {
      foundAsset = assets.find(a => a.serial_number.toLowerCase() === serial_number.toLowerCase());
    }

    if (foundAsset) {
      setScannedAsset(foundAsset);
      setSuccess('Asset found via OCR!');
      setTimeout(() => setSuccess(null), 3000);
    } else {
      setError('Asset not found in local database. Try "Add" to create it.');
      if (asset_tag || serial_number) {
        setNewItem(prev => ({
          ...prev,
          asset_tag: asset_tag || prev.asset_tag,
          serial_number: serial_number || prev.serial_number,
        }));
      }
      setTimeout(() => setError(null), 5000);
    }
  };

  const startScanner = () => {
    setScanning(true);
    setScannedAsset(null);

    setTimeout(() => {
      const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
      };

      const scanner = new Html5QrcodeScanner('mobile-qr-reader', config, false);

      scanner.render(
        async (decodedText: string) => {
          try {
            const data = JSON.parse(decodedText);
            if (data.id) {
              const response = await axios.get(`${API_URL}/api/v1/assets/${data.id}`);
              setScannedAsset(response.data);
              scanner.clear();
              setScanning(false);
            }
          } catch (err) {
            setError('Invalid QR code or asset not found');
            logger.error('Scan error:', err);
          }
        },
        (errorMessage: string) => {
          if (!errorMessage.includes('NotFoundException')) {
            logger.warn('Scan error:', errorMessage);
          }
        }
      );

      setScannerInstance(scanner);
    }, 100);
  };

  const stopScanner = () => {
    if (scannerInstance) {
      scannerInstance.clear().catch((err) => logger.error('Error clearing scanner:', err));
      setScannerInstance(null);
    }
    setScanning(false);
  };

  const updateAssetStatus = async (assetId: number, newStatus: string) => {
    try {
      await axios.put(`${API_URL}/api/v1/assets/${assetId}`, { status: newStatus });
      setSuccess(`Status updated to ${newStatus}`);
      fetchAssets();
      if (scannedAsset && scannedAsset.id === assetId) {
        setScannedAsset({ ...scannedAsset, status: newStatus });
      }
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to update status');
      setTimeout(() => setError(null), 3000);
    }
  };

  const updateAssetQuantity = async (asset: Asset, change: number) => {
    const currentQuantity = asset.custom_fields?.quantity || 1;
    const newQuantity = Math.max(0, currentQuantity + change);

    try {
      await axios.put(`${API_URL}/api/v1/assets/${asset.id}`, {
        custom_fields: {
          ...asset.custom_fields,
          quantity: newQuantity
        }
      });
      setSuccess(`Quantity updated to ${newQuantity}`);
      fetchAssets();
      if (scannedAsset && scannedAsset.id === asset.id) {
        setScannedAsset({
          ...scannedAsset,
          custom_fields: { ...scannedAsset.custom_fields, quantity: newQuantity }
        });
      }
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to update quantity');
      setTimeout(() => setError(null), 3000);
    }
  };

  // Generate serial number and asset tag from backend
  const generateSerialAndTag = async () => {
    if (!newItem.asset_type) {
      setError('Please select an asset type first');
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');
      const response = await axios.post(`${API_URL}/api/v1/assets/generate-serial`, {
        asset_type: newItem.asset_type
      }, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setNewItem({
        ...newItem,
        asset_tag: response.data.asset_tag,
        serial_number: response.data.serial_number
      });
      setSuccess('Generated unique identifiers');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate serial');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const addNewAsset = async () => {
    try {
      setLoading(true);
      const payload: any = {
        asset_tag: newItem.asset_tag,
        serial_number: newItem.serial_number,
        asset_type: newItem.asset_type,
        manufacturer: newItem.manufacturer,
        model: newItem.model,
        status: newItem.status
      };

      if (newItem.hostname) payload.hostname = newItem.hostname;
      if (newItem.quantity > 1) {
        payload.custom_fields = { quantity: newItem.quantity };
      }

      await axios.post(`${API_URL}/api/v1/assets/`, payload);
      setSuccess('Asset added successfully!');
      setNewItem({
        asset_tag: '',
        serial_number: '',
        asset_type: '',
        manufacturer: '',
        model: '',
        hostname: '',
        status: 'received',
        quantity: 1
      });
      fetchAssets();
      setLoading(false);
      setTimeout(() => {
        setSuccess(null);
        setCurrentView('home');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add asset');
      setLoading(false);
      setTimeout(() => setError(null), 5000);
    }
  };

  const deleteAsset = async (assetId: number) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) return;

    try {
      await axios.delete(`${API_URL}/api/v1/assets/${assetId}`);
      setSuccess('Asset deleted');
      fetchAssets();
      setScannedAsset(null);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to delete asset');
      setTimeout(() => setError(null), 3000);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: { [key: string]: { bg: string; text: string } } = {
      received: { bg: 'rgba(0, 123, 255, 0.1)', text: 'var(--primary)' },
      deployed: { bg: 'rgba(16, 185, 129, 0.1)', text: 'var(--success)' },
      in_use: { bg: 'rgba(147, 51, 234, 0.1)', text: '#a855f7' },
      storage: { bg: 'var(--bg-light)', text: 'var(--text-dark)' },
      maintenance: { bg: 'rgba(245, 158, 11, 0.1)', text: 'var(--warning)' },
      retired: { bg: 'rgba(239, 68, 68, 0.1)', text: 'var(--danger)' }
    };
    const color = colors[status] || { bg: 'var(--bg-light)', text: 'var(--text-dark)' };
    return { style: { backgroundColor: color.bg, color: color.text } };
  };

  const getStatsSummary = () => {
    const assetArray = Array.isArray(assets) ? assets : [];
    const stats = {
      total: assetArray.length,
      received: assetArray.filter(a => a.status === 'received').length,
      deployed: assetArray.filter(a => a.status === 'deployed').length,
      storage: assetArray.filter(a => a.status === 'storage').length,
      maintenance: assetArray.filter(a => a.status === 'maintenance').length
    };
    return stats;
  };

  const stats = getStatsSummary();

  return (
    <div className="min-h-screen bg-page">
      {/* Header */}
      <div className="text-white p-4 shadow-lg" style={{ backgroundColor: 'var(--primary)' }}>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">RackPlane Mobile</h1>
          <button
            onClick={() => navigate('/assets')}
            className="text-sm px-3 py-1 rounded"
            style={{ backgroundColor: 'var(--primary-dark)' }}
          >
            Desktop
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="text-white px-4 py-3 text-center" style={{ backgroundColor: 'var(--danger)' }}>
          {error}
        </div>
      )}
      {success && (
        <div className="text-white px-4 py-3 text-center" style={{ backgroundColor: 'var(--success)' }}>
          {success}
        </div>
      )}

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-card border-t shadow-lg z-50" style={{ borderColor: 'var(--border-color)' }}>
        <div className="grid grid-cols-4 gap-1">
          <button
            onClick={() => {
              setCurrentView('home');
              stopScanner();
            }}
            className={`p-3 text-center ${currentView === 'home' ? 'text-primary' : 'text-gray-500 dark:text-gray-400'}`}
            style={currentView === 'home' ? { backgroundColor: 'rgba(0, 123, 255, 0.1)' } : {}}
          >
            <div className="text-2xl">🏠</div>
            <div className="text-xs">Home</div>
          </button>
          <button
            onClick={() => {
              setCurrentView('scan');
              setScannedAsset(null);
            }}
            className={`p-3 text-center ${currentView === 'scan' ? 'text-primary' : 'text-gray-500 dark:text-gray-400'}`}
            style={currentView === 'scan' ? { backgroundColor: 'rgba(0, 123, 255, 0.1)' } : {}}
          >
            <div className="text-2xl">📷</div>
            <div className="text-xs">Scan</div>
          </button>
          <button
            onClick={() => {
              setCurrentView('add');
              stopScanner();
            }}
            className={`p-3 text-center ${currentView === 'add' ? 'text-primary' : 'text-gray-500 dark:text-gray-400'}`}
            style={currentView === 'add' ? { backgroundColor: 'rgba(0, 123, 255, 0.1)' } : {}}
          >
            <div className="text-2xl">➕</div>
            <div className="text-xs">Add</div>
          </button>
          <button
            onClick={() => {
              setCurrentView('inventory');
              stopScanner();
            }}
            className={`p-3 text-center ${currentView === 'inventory' ? 'text-primary' : 'text-gray-500 dark:text-gray-400'}`}
            style={currentView === 'inventory' ? { backgroundColor: 'rgba(0, 123, 255, 0.1)' } : {}}
          >
            <div className="text-2xl">📦</div>
            <div className="text-xs">Items</div>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="pb-20 p-4">
        {/* HOME VIEW */}
        {currentView === 'home' && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-primary mb-4">Dashboard</h2>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-card rounded-lg shadow p-4">
                <div className="text-3xl font-bold" style={{ color: 'var(--primary)' }}>{stats.total}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Assets</div>
              </div>
              <div className="bg-card rounded-lg shadow p-4">
                <div className="text-3xl font-bold" style={{ color: 'var(--success)' }}>{stats.deployed}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Deployed</div>
              </div>
              <div className="bg-card rounded-lg shadow p-4">
                <div className="text-3xl font-bold" style={{ color: 'var(--warning)' }}>{stats.received}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Received</div>
              </div>
              <div className="bg-card rounded-lg shadow p-4">
                <div className="text-3xl font-bold" style={{ color: '#a855f7' }}>{stats.storage}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">In Storage</div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-card rounded-lg shadow p-4">
              <h3 className="font-bold text-primary mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={() => setCurrentView('scan')}
                  className="w-full text-white p-3 rounded-lg font-medium"
                  style={{ backgroundColor: 'var(--primary)' }}
                >
                  📷 Scan Item
                </button>
                <button
                  onClick={() => setCurrentView('add')}
                  className="w-full text-white p-3 rounded-lg font-medium"
                  style={{ backgroundColor: 'var(--success)' }}
                >
                  ➕ Add New Item
                </button>
                <button
                  onClick={() => setCurrentView('inventory')}
                  className="w-full text-white p-3 rounded-lg font-medium"
                  style={{ backgroundColor: '#a855f7' }}
                >
                  📦 View Inventory
                </button>
              </div>
            </div>

            {/* Recent Items */}
            <div className="bg-card rounded-lg shadow p-4">
              <h3 className="font-bold text-primary mb-3">Recently Added</h3>
              <div className="space-y-2">
                {Array.isArray(assets) && assets.length > 0 ? (
                  assets.slice(0, 5).map(asset => (
                    <div key={asset.id} className="border rounded p-2" style={{ borderColor: 'var(--border-color)' }}>
                      <div className="font-medium text-sm text-primary">{asset.asset_tag}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">{asset.manufacturer} {asset.model}</div>
                      <span className="text-xs px-2 py-1 rounded" {...getStatusColor(asset.status)}>
                        {formatStatus(asset.status)}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                    No assets yet. Add your first item!
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* SCAN VIEW */}
        {currentView === 'scan' && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-primary mb-4">Scan Item</h2>

            {/* Scan Mode Toggle */}
            {!scannedAsset && (
              <div className="flex gap-2 mb-4 bg-card p-1 rounded-lg shadow-sm">
                <button
                  onClick={() => {
                    setScanMode('qr');
                    stopScanner();
                  }}
                  className={`flex-1 p-2 rounded-md text-sm font-medium transition-colors ${scanMode === 'qr' ? 'text-white' : 'bg-transparent text-gray-500 dark:text-gray-400 hover:bg-table-row-hover'}`}
                  style={scanMode === 'qr' ? { backgroundColor: 'var(--primary)' } : {}}
                >
                  QR Code
                </button>
                <button
                  onClick={() => {
                    setScanMode('ocr');
                    stopScanner();
                  }}
                  className={`flex-1 p-2 rounded-md text-sm font-medium transition-colors ${scanMode === 'ocr' ? 'text-white' : 'bg-transparent text-gray-500 dark:text-gray-400 hover:bg-table-row-hover'}`}
                  style={scanMode === 'ocr' ? { backgroundColor: 'var(--primary)' } : {}}
                >
                  {isPremium ? 'Photo / OCR' : 'Photo'}
                </button>
              </div>
            )}

            {/* QR Scanner Mode */}
            {scanMode === 'qr' && !scanning && !scannedAsset && (
              <button
                onClick={startScanner}
                className="w-full text-white p-4 rounded-lg text-lg font-medium shadow"
                style={{ backgroundColor: 'var(--primary)' }}
              >
                📷 Start QR Scanner
              </button>
            )}

            {scanMode === 'qr' && scanning && (
              <div className="bg-card rounded-lg shadow p-4">
                <div id="mobile-qr-reader" className="w-full"></div>
                <button
                  onClick={stopScanner}
                  className="w-full mt-4 text-white p-3 rounded-lg"
                  style={{ backgroundColor: 'var(--danger)' }}
                >
                  Stop Scanning
                </button>
              </div>
            )}

            {/* OCR Mode */}
            {scanMode === 'ocr' && !scannedAsset && (
              <div className="bg-card rounded-lg shadow p-4">
                <ImageUploadOCR onOCRComplete={handleOCRComplete} />
              </div>
            )}

            {scannedAsset && (
              <div className="bg-card rounded-lg shadow p-4 space-y-4">
                <div className="border-b pb-3">
                  <h3 className="text-xl font-bold text-primary">{scannedAsset.asset_tag}</h3>
                  <p className="text-gray-500 dark:text-gray-400">{scannedAsset.manufacturer} {scannedAsset.model}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">S/N: {scannedAsset.serial_number}</p>
                  {scannedAsset.hostname && (
                    <p className="text-sm text-gray-500 dark:text-gray-400">Host: {scannedAsset.hostname}</p>
                  )}
                </div>

                {/* Current Status */}
                <div>
                  <label className="text-sm font-medium text-primary">Current Status</label>
                  <div className="mt-1 px-3 py-2 rounded inline-block" {...getStatusColor(scannedAsset.status)}>
                    {scannedAsset.status}
                  </div>
                </div>

                {/* Quantity Management */}
                {scannedAsset.custom_fields?.quantity && scannedAsset.custom_fields.quantity > 1 && (
                  <div>
                    <label className="text-sm font-medium text-primary">Quantity</label>
                    <div className="flex items-center gap-3 mt-2">
                      <button
                        onClick={() => updateAssetQuantity(scannedAsset, -1)}
                        className="text-white w-12 h-12 rounded-lg text-2xl font-bold"
                        style={{ backgroundColor: 'var(--danger)' }}
                        disabled={scannedAsset.custom_fields.quantity <= 0}
                      >
                        -
                      </button>
                      <div className="text-3xl font-bold text-primary">
                        {scannedAsset.custom_fields.quantity}
                      </div>
                      <button
                        onClick={() => updateAssetQuantity(scannedAsset, 1)}
                        className="text-white w-12 h-12 rounded-lg text-2xl font-bold"
                        style={{ backgroundColor: 'var(--success)' }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                )}

                {/* Change Status */}
                <div>
                  <label className="text-sm font-medium text-primary mb-2 block">Change Status</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['received', 'deployed', 'storage', 'maintenance', 'retired'].map(status => (
                      <button
                        key={status}
                        onClick={() => updateAssetStatus(scannedAsset.id, status)}
                        className={`p-2 rounded text-sm font-medium ${scannedAsset.status === status ? 'text-white' : 'text-primary'}`}
                        style={scannedAsset.status === status
                          ? { backgroundColor: 'var(--primary)' }
                          : { backgroundColor: 'var(--bg-light)' }
                        }
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                  <button
                    onClick={() => {
                      setPrintingAsset(scannedAsset);
                      setShowLabelPrint(true);
                    }}
                    className="w-full text-white p-3 rounded-lg font-medium"
                    style={{ backgroundColor: '#a855f7' }}
                  >
                    🏷️ Print Label
                  </button>
                  <button
                    onClick={() => navigate(`/assets/${scannedAsset.id}`)}
                    className="w-full text-white p-3 rounded-lg font-medium"
                    style={{ backgroundColor: 'var(--secondary)' }}
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => deleteAsset(scannedAsset.id)}
                    className="w-full text-white p-3 rounded-lg font-medium"
                    style={{ backgroundColor: 'var(--danger)' }}
                  >
                    Delete Asset
                  </button>
                  <button
                    onClick={() => {
                      setScannedAsset(null);
                      startScanner();
                    }}
                    className="w-full text-white p-3 rounded-lg font-medium"
                    style={{ backgroundColor: 'var(--primary)' }}
                  >
                    Scan Another
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ADD VIEW */}
        {currentView === 'add' && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-primary mb-4">Add New Item</h2>

            <div className="bg-card rounded-lg shadow p-4 space-y-4">
              {newItem.asset_type && (
                <button
                  type="button"
                  onClick={generateSerialAndTag}
                  disabled={loading}
                  className="w-full text-white py-3 rounded-lg font-semibold text-lg"
                  style={{ backgroundColor: 'var(--primary)' }}
                >
                  {loading ? 'Generating...' : '🔄 Generate Asset Tag & Serial'}
                </button>
              )}

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Asset Tag *</label>
                <input
                  type="text"
                  value={newItem.asset_tag}
                  onChange={(e) => setNewItem({ ...newItem, asset_tag: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                  placeholder="Click Generate or enter manually"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Serial Number *</label>
                <input
                  type="text"
                  value={newItem.serial_number}
                  onChange={(e) => setNewItem({ ...newItem, serial_number: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                  placeholder="Click Generate or enter manually"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Asset Type *</label>
                <select
                  value={newItem.asset_type}
                  onChange={(e) => setNewItem({ ...newItem, asset_type: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  <option value="">Select Type</option>
                  {assetTypes.map(type => (
                    <option key={type.id} value={type.name}>{type.display_name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Manufacturer *</label>
                <input
                  type="text"
                  value={newItem.manufacturer}
                  onChange={(e) => setNewItem({ ...newItem, manufacturer: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                  placeholder="e.g., Dell"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Model *</label>
                <input
                  type="text"
                  value={newItem.model}
                  onChange={(e) => setNewItem({ ...newItem, model: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                  placeholder="e.g., PowerEdge R740"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Hostname</label>
                <input
                  type="text"
                  value={newItem.hostname}
                  onChange={(e) => setNewItem({ ...newItem, hostname: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                  placeholder="Optional"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Quantity</label>
                <input
                  type="number"
                  value={newItem.quantity}
                  onChange={(e) => setNewItem({ ...newItem, quantity: parseInt(e.target.value) || 1 })}
                  min="1"
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">For bulk items (cables, cards, etc.)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-1">Status</label>
                <select
                  value={newItem.status}
                  onChange={(e) => setNewItem({ ...newItem, status: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-base"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  <option value="received">Received</option>
                  <option value="deployed">Deployed</option>
                  <option value="storage">Storage</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="retired">Retired</option>
                </select>
              </div>

              <button
                onClick={addNewAsset}
                disabled={loading || !newItem.asset_tag || !newItem.serial_number || !newItem.asset_type || !newItem.manufacturer || !newItem.model}
                className="w-full text-white p-3 rounded-lg font-medium text-lg"
                style={{ backgroundColor: 'var(--success)' }}
              >
                {loading ? 'Adding...' : 'Add Asset'}
              </button>
            </div>
          </div>
        )}

        {/* INVENTORY VIEW */}
        {currentView === 'inventory' && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-primary mb-4">Inventory</h2>

            {/* Search and Filter */}
            <div className="bg-card rounded-lg shadow p-4 space-y-3">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search assets..."
                className="w-full border rounded-lg px-3 py-2 text-base"
                style={{ borderColor: 'var(--border-color)' }}
              />

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-base"
                style={{ borderColor: 'var(--border-color)' }}
              >
                <option value="all">All Statuses</option>
                <option value="received">Received</option>
                <option value="deployed">Deployed</option>
                <option value="storage">Storage</option>
                <option value="maintenance">Maintenance</option>
                <option value="retired">Retired</option>
              </select>
            </div>

            {/* Asset List */}
            <div className="space-y-3">
              {loading ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading...</div>
              ) : filteredAssets.length === 0 ? (
                <div className="bg-card rounded-lg shadow p-8 text-center text-gray-500 dark:text-gray-400">
                  No assets found
                </div>
              ) : (
                filteredAssets.map(asset => (
                  <div key={asset.id} className="bg-card rounded-lg shadow p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h3 className="font-bold text-primary">{asset.asset_tag}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">{asset.manufacturer} {asset.model}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">S/N: {asset.serial_number}</p>
                        {asset.custom_fields?.quantity && asset.custom_fields.quantity > 1 && (
                          <p className="text-xs font-medium" style={{ color: 'var(--primary)' }}>Qty: {asset.custom_fields.quantity}</p>
                        )}
                      </div>
                      <span className="text-xs px-2 py-1 rounded" {...getStatusColor(asset.status)}>
                        {formatStatus(asset.status)}
                      </span>
                    </div>

                    <div className="flex gap-2 mt-3">
                      {asset.custom_fields?.quantity && asset.custom_fields.quantity > 1 && (
                        <>
                          <button
                            onClick={() => updateAssetQuantity(asset, -1)}
                            className="flex-1 text-white py-2 rounded text-sm"
                            style={{ backgroundColor: 'var(--danger)' }}
                          >
                            - Qty
                          </button>
                          <button
                            onClick={() => updateAssetQuantity(asset, 1)}
                            className="flex-1 text-white py-2 rounded text-sm"
                            style={{ backgroundColor: 'var(--success)' }}
                          >
                            + Qty
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => {
                          setPrintingAsset(asset);
                          setShowLabelPrint(true);
                        }}
                        className="flex-1 text-white py-2 rounded text-sm"
                        style={{ backgroundColor: '#a855f7' }}
                      >
                        🏷️ Label
                      </button>
                      <button
                        onClick={() => navigate(`/assets/${asset.id}`)}
                        className="flex-1 text-white py-2 rounded text-sm"
                        style={{ backgroundColor: 'var(--primary)' }}
                      >
                        View
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Label Print Modal */}
      {printingAsset && (
        <LabelPrintModal
          isOpen={showLabelPrint}
          onClose={() => {
            setShowLabelPrint(false);
            setPrintingAsset(null);
          }}
          item={printingAsset}
          itemType="asset"
        />
      )}
    </div>
  );
};

export default MobileDCMS;
