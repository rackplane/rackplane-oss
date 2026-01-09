// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import logger from '../utils/logger';
import { formatAssetType } from '../utils/formatAssetType';
import SourceBadge from '../components/SourceBadge';
import DeviceTypeImportModal from '../components/DeviceTypeImportModal';
import { useCapabilities } from '../contexts/CapabilityContext';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { FeatureGate } from '../components/FeatureGate';
import { formatError } from '../utils/errorFormatters';

interface VendorSKU {
  id: number;
  vendor: string;
  sku: string;
  part_number?: string;
  name: string;
  manufacturer?: string;
  asset_type?: string;
  specifications?: Record<string, any>;
  price_usd?: number;
  currency: string;
  compatibility?: Record<string, any>;
  description?: string;
  datasheet_url?: string;
  vendor_url?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface VendorSKUFormData {
  vendor: string;
  sku: string;
  part_number: string;
  name: string;
  manufacturer: string;
  asset_type: string;
  specifications: string; // JSON string for editing
  price_usd: string;
  currency: string;
  compatibility: string; // JSON string for editing
  description: string;
  datasheet_url: string;
  vendor_url: string;
  notes: string;
}

const VendorSKUs: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { addToCart } = useCart();
  const [vendorSKUs, setVendorSKUs] = useState<VendorSKU[]>([]);
  const [vendors, setVendors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const { checkCapability } = useCapabilities();
  const hasGlobalCatalog = checkCapability('global_catalog');
  const hasVendorApis = checkCapability('vendor_apis');

  const [showModal, setShowModal] = useState(false);
  const [showDeviceTypeModal, setShowDeviceTypeModal] = useState(false);
  const [editingSKU, setEditingSKU] = useState<VendorSKU | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterVendor, setFilterVendor] = useState<string>('');
  const [filterAssetType, setFilterAssetType] = useState<string>('');
  const [formData, setFormData] = useState<VendorSKUFormData>({
    vendor: '',
    sku: '',
    part_number: '',
    name: '',
    manufacturer: '',
    asset_type: '',
    specifications: '{}',
    price_usd: '',
    currency: 'USD',
    compatibility: '{}',
    description: '',
    datasheet_url: '',
    vendor_url: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Reserved for future debounce implementation
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [searchDebounceTimer, setSearchDebounceTimer] = useState<NodeJS.Timeout | null>(null);
  const [showSampleModal, setShowSampleModal] = useState(false);
  const [sampleSKUs, setSampleSKUs] = useState<VendorSKU[]>([]);
  const [loadingSample, setLoadingSample] = useState(false);
  const [sampleSearchTerm, setSampleSearchTerm] = useState('');
  const [sampleFilterVendor, setSampleFilterVendor] = useState<string>('');
  const [sampleFilterAssetType, setSampleFilterAssetType] = useState<string>('');
  const [sampleTotalAvailable, setSampleTotalAvailable] = useState(0);
  const [samplePage, setSamplePage] = useState(1);
  const [sampleMessage, setSampleMessage] = useState('');
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [punchoutConfigured, setPunchoutConfigured] = useState(false);
  const [importingSKU, setImportingSKU] = useState<number | null>(null);
  const [assetTypes] = useState([
    { value: 'server', label: 'Server' },
    { value: 'switch', label: 'Switch' },
    { value: 'router', label: 'Router' },
    { value: 'storage', label: 'Storage' },
    { value: 'pdu', label: 'PDU' },
    { value: 'ups', label: 'UPS' },
    { value: 'dac_cable', label: 'DAC Cable' },
    { value: 'aoc_cable', label: 'AOC Cable' },
    { value: 'transceiver', label: 'Transceiver' },
    { value: 'nic', label: 'NIC' },
    { value: 'gpu', label: 'GPU' },
    { value: 'memory', label: 'Memory' },
    { value: 'cpu', label: 'CPU' },
    { value: 'ssd', label: 'SSD' },
    { value: 'hdd', label: 'HDD' },
    { value: 'cable', label: 'Cable' },
    { value: 'patch_panel', label: 'Patch Panel' },
    { value: 'other', label: 'Other' }
  ]);

  // Helper to get display name for asset type - uses centralized formatAssetType utility
  const getAssetTypeLabel = formatAssetType;

  const fetchVendorSKUs = async () => {
    try {
      setLoading(true);
      const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
      const params: any = {};
      if (searchTerm) params.search = searchTerm;
      if (filterVendor) params.vendor = filterVendor;
      if (filterAssetType) params.asset_type = filterAssetType;

      const response = await axios.get(`${API_URL}/api/v1/vendor-skus/`, { headers, params });
      setVendorSKUs(response.data);

      // Extract unique vendors for filter (only on initial load without filters)
      if (!searchTerm && !filterVendor && !filterAssetType) {
        const uniqueVendors = Array.from(new Set(response.data.map((sku: VendorSKU) => sku.vendor))) as string[];
        setVendors(uniqueVendors);
      }
    } catch (error) {
      logger.error('Error fetching vendor SKUs:', error);
      setError('Failed to load vendor SKUs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchVendorSKUs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // Check if Amazon Punchout is configured
  useEffect(() => {
    const checkPunchoutStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/v1/punchout/amazon/status`);
        setPunchoutConfigured(response.data.configured || false);
      } catch {
        setPunchoutConfigured(false);
      }
    };
    if (isAuthenticated) {
      checkPunchoutStatus();
    }
  }, [isAuthenticated]);

  // Refetch when filters change (with debounce for search)
  useEffect(() => {
    if (!isAuthenticated) return;
    const timer = setTimeout(() => {
      fetchVendorSKUs();
    }, searchTerm ? 500 : 0); // Debounce search, immediate for dropdowns
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterVendor, filterAssetType]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingSKU(null);
    setFormData({
      vendor: '',
      sku: '',
      part_number: '',
      name: '',
      manufacturer: '',
      asset_type: '',
      specifications: '{}',
      price_usd: '',
      currency: 'USD',
      compatibility: '{}',
      description: '',
      datasheet_url: '',
      vendor_url: '',
      notes: '',
    });
    setError(null);
  };

  const startEdit = (sku: VendorSKU) => {
    setEditingSKU(sku);
    setFormData({
      vendor: sku.vendor,
      sku: sku.sku,
      part_number: sku.part_number || '',
      name: sku.name,
      manufacturer: sku.manufacturer || '',
      asset_type: sku.asset_type || '',
      specifications: JSON.stringify(sku.specifications || {}, null, 2),
      price_usd: sku.price_usd?.toString() || '',
      currency: sku.currency,
      compatibility: JSON.stringify(sku.compatibility || {}, null, 2),
      description: sku.description || '',
      datasheet_url: sku.datasheet_url || '',
      vendor_url: sku.vendor_url || '',
      notes: sku.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload = {
        ...formData,
        price_usd: formData.price_usd ? parseFloat(formData.price_usd) : null,
        specifications: JSON.parse(formData.specifications || '{}'),
        compatibility: JSON.parse(formData.compatibility || '{}'),
      };

      const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };

      if (editingSKU) {
        await axios.put(`${API_URL}/api/v1/vendor-skus/${editingSKU.id}`, payload, { headers });
      } else {
        await axios.post(`${API_URL}/api/v1/vendor-skus/`, payload, { headers });
      }

      closeModal();
      fetchVendorSKUs();
    } catch (error: any) {
      logger.error('Error saving SKU:', error);
      setError(formatError(error.response?.data?.detail || 'Failed to save SKU'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-primary">Vendor SKUs</h1>
        <div className="flex gap-3">
          <button
            onClick={() => {
              setShowModal(true);
              setError(null);
            }}
            className="btn-primary"
          >
            <svg className="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add SKU
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-destructive rounded">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-card rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Search</label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search SKU, name, description..."
              className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Vendor</label>
            <select
              value={filterVendor}
              onChange={(e) => setFilterVendor(e.target.value)}
              className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
            >
              <option value="">All Vendors</option>
              {vendors.map(vendor => (
                <option key={vendor} value={vendor}>{vendor}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Asset Type</label>
            <select
              value={filterAssetType}
              onChange={(e) => setFilterAssetType(e.target.value)}
              className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
            >
              <option value="">All Types</option>
              {assetTypes.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterVendor('');
                setFilterAssetType('');
              }}
              className="btn-secondary w-full"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* SKU List */}
      {loading ? (
        <div className="text-center py-8">Loading vendor SKUs...</div>
      ) : vendorSKUs.length === 0 ? (
        <div className="bg-card rounded-lg shadow p-8 text-center">
          <p className="text-muted-foreground mb-4">No vendor SKUs found.</p>
          <button
            onClick={() => {
              setShowModal(true);
              setError(null);
            }}
            className="btn-primary"
          >
            Add Your First SKU
          </button>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-subtle-card">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Vendor</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">SKU</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Part Number</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Asset Type</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Price</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-primary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-color">
                {vendorSKUs.map((sku) => (
                  <tr key={sku.id} className="hover:bg-subtle-card">
                    <td className="px-4 py-3 text-sm text-muted-foreground">{sku.vendor}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{sku.sku}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{sku.part_number || '-'}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{sku.name}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{getAssetTypeLabel(sku.asset_type)}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {sku.price_usd ? `$${sku.price_usd.toFixed(2)} ${sku.currency}` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      <div className="flex gap-2">
                        <button
                          onClick={async () => {
                            await addToCart({ vendor_sku_id: sku.id, quantity: 1 });
                          }}
                          className="text-blue-600 hover:text-blue-700"
                          title="Add to Cart"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                          </svg>
                        </button>
                        {/* Edit button only for local SKUs (positive IDs) */}
                        {sku.id > 0 && (
                          <button
                            onClick={() => startEdit(sku)}
                            className="text-primary hover:text-primary/80"
                            title="Edit"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                        )}
                        <button
                          onClick={() => {
                            // Infer asset type if not set
                            let assetType = sku.asset_type;
                            if (!assetType) {
                              const name = (sku.name || '').toLowerCase();
                              const desc = (sku.description || '').toLowerCase();
                              const combined = `${name} ${desc}`;

                              // Infer from keywords
                              if (combined.includes('dac') || combined.includes('direct attach')) {
                                assetType = 'dac_cable';
                              } else if (combined.includes('aoc') || combined.includes('active optical')) {
                                assetType = 'aoc_cable';
                              } else if (combined.includes('fiber') || combined.includes('optical cable')) {
                                assetType = 'fiber_cable';
                              } else if (combined.includes('transceiver') || combined.includes('sfp') || combined.includes('qsfp')) {
                                assetType = 'transceiver';
                              } else if (combined.includes('switch')) {
                                assetType = 'switch';
                              } else if (combined.includes('server')) {
                                assetType = 'server';
                              } else if (combined.includes('pdu') || combined.includes('power distribution')) {
                                assetType = 'pdu';
                              } else if (combined.includes('cable') && !combined.includes('fiber') && !combined.includes('dac') && !combined.includes('aoc')) {
                                assetType = 'cable';
                              } else {
                                assetType = 'other';
                              }
                            }

                            const params = new URLSearchParams({
                              manufacturer: sku.manufacturer || sku.vendor,
                              model: sku.name,
                              asset_type: assetType,
                              sku: sku.sku
                            });
                            navigate(`/assets?modal=create&${params.toString()}`);
                          }}
                          className="text-green-600 hover:text-green-700"
                          title="Create Asset from SKU"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                          </svg>
                        </button>
                        {sku.vendor_url && (
                          <a
                            href={sku.vendor_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:text-primary/80"
                            title="Vendor Page"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}


      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-card rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-primary mb-4">
                {editingSKU ? 'Edit Vendor SKU' : 'Add Vendor SKU'}
              </h2>

              {error && (
                <div className="mb-4 p-3 bg-destructive/10 border border-destructive/50 text-destructive rounded">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Vendor *
                    </label>
                    <input
                      type="text"
                      name="vendor"
                      value={formData.vendor}
                      onChange={handleInputChange}
                      required
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="e.g., FS.com, NVIDIA"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      SKU *
                    </label>
                    <input
                      type="text"
                      name="sku"
                      value={formData.sku}
                      onChange={handleInputChange}
                      required
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="e.g., 229577 (vendor's internal SKU)"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Vendor's internal SKU number
                    </p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Part Number
                  </label>
                  <input
                    type="text"
                    name="part_number"
                    value={formData.part_number}
                    onChange={handleInputChange}
                    className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                    placeholder="e.g., OSFP-800G-PC01 (customer-facing part number)"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Customer-facing part number (e.g., OSFP-800G-PC01)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Product Name *
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                    placeholder="e.g., 100G QSFP28 DAC Cable 3m"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Manufacturer
                    </label>
                    <input
                      type="text"
                      name="manufacturer"
                      value={formData.manufacturer}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="e.g., FS.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Asset Type
                    </label>
                    <input
                      type="text"
                      name="asset_type"
                      value={formData.asset_type}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="e.g., dac_cable, optical_transceiver"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Specifications (JSON)
                  </label>
                  <textarea
                    name="specifications"
                    value={formData.specifications}
                    onChange={handleInputChange}
                    rows={6}
                    className="w-full border border-input rounded px-3 py-2 font-mono text-sm bg-background text-foreground"
                    placeholder='{"speed": "100G", "length": "3m", "connector_a": "QSFP28"}'
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    JSON object with product specifications (speed, length, connectors, etc.)
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Price (USD)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      name="price_usd"
                      value={formData.price_usd}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="45.99"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Currency
                    </label>
                    <select
                      name="currency"
                      value={formData.currency}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Compatibility (JSON)
                  </label>
                  <textarea
                    name="compatibility"
                    value={formData.compatibility}
                    onChange={handleInputChange}
                    rows={4}
                    className="w-full border border-input rounded px-3 py-2 font-mono text-sm bg-background text-foreground"
                    placeholder='{"compatible_with": ["Cisco Nexus 9000"], "notes": "..."}'
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Description
                  </label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleInputChange}
                    rows={3}
                    className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                    placeholder="Product description..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Vendor URL
                    </label>
                    <input
                      type="url"
                      name="vendor_url"
                      value={formData.vendor_url}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="https://www.fs.com/products/12345.html"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                      Datasheet URL
                    </label>
                    <input
                      type="url"
                      name="datasheet_url"
                      value={formData.datasheet_url}
                      onChange={handleInputChange}
                      className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                      placeholder="https://..."
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Notes
                  </label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleInputChange}
                    rows={2}
                    className="w-full border border-input rounded px-3 py-2 bg-background text-foreground"
                    placeholder="Internal notes..."
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    disabled={saving}
                    className="btn-primary flex-1"
                  >
                    {saving ? 'Saving...' : editingSKU ? 'Update SKU' : 'Create SKU'}
                  </button>
                  <button
                    type="button"
                    onClick={closeModal}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )
      }

      <DeviceTypeImportModal
        isOpen={showDeviceTypeModal}
        onClose={() => setShowDeviceTypeModal(false)}
        onImport={(sku) => {
          setShowDeviceTypeModal(false);
          fetchVendorSKUs();
          // Show success message (optional - could add toast notification)
          setError(null);
        }}
      />

    </div>
  );
};

export default VendorSKUs;

