import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

export interface EnrichProductModalProps {
    isOpen: boolean;
    onClose: () => void;
    product: {
        id: number;
        vendor: string;
        sku: string;
        vendor_product_id?: string;
        name?: string;
        product_name?: string;
        price_usd?: number;
        manufacturer?: string;
        description?: string;
        compatibility?: string[];
        specifications?: Record<string, any>;
        datasheet_url?: string;
        vendor_url?: string;
        image_url?: string;
    } | null;
    onEnriched?: (updatedProduct: any) => void;
}

const EnrichProductModal: React.FC<EnrichProductModalProps> = ({
    isOpen,
    onClose,
    product,
    onEnriched
}) => {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Form state
    const [priceUsd, setPriceUsd] = useState<string>('');
    const [stockStatus, setStockStatus] = useState<string>('');
    const [leadTime, setLeadTime] = useState<string>('');
    const [compatibility, setCompatibility] = useState<string>('');
    const [description, setDescription] = useState<string>('');
    const [manufacturer, setManufacturer] = useState<string>('');
    const [datasheetUrl, setDatasheetUrl] = useState<string>('');
    const [vendorUrl, setVendorUrl] = useState<string>('');

    // New spec key/value inputs
    const [newSpecKey, setNewSpecKey] = useState<string>('');
    const [newSpecValue, setNewSpecValue] = useState<string>('');
    const [additionalSpecs, setAdditionalSpecs] = useState<Record<string, string>>({});

    // Populate form when product changes
    useEffect(() => {
        if (product) {
            setPriceUsd(product.price_usd?.toString() || '');
            setStockStatus(product.specifications?.stock_status || '');
            setLeadTime(product.specifications?.lead_time || '');
            setCompatibility(product.compatibility?.join(', ') || '');
            setDescription(product.description || '');
            setManufacturer(product.manufacturer || '');
            setDatasheetUrl(product.datasheet_url || '');
            setVendorUrl(product.vendor_url || '');
            setAdditionalSpecs({});
            setError(null);
            setSuccess(null);
        }
    }, [product]);

    const handleAddSpec = () => {
        if (newSpecKey.trim() && newSpecValue.trim()) {
            setAdditionalSpecs(prev => ({
                ...prev,
                [newSpecKey.trim()]: newSpecValue.trim()
            }));
            setNewSpecKey('');
            setNewSpecValue('');
        }
    };

    const handleRemoveSpec = (key: string) => {
        setAdditionalSpecs(prev => {
            const updated = { ...prev };
            delete updated[key];
            return updated;
        });
    };

    const handleSave = async () => {
        if (!product) return;

        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            const headers = {
                Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
                'Content-Type': 'application/json'
            };

            // Build payload
            const payload: any = {};
            if (priceUsd) payload.price_usd = parseFloat(priceUsd);
            if (stockStatus) payload.stock_status = stockStatus;
            if (leadTime) payload.lead_time = leadTime;

            // Compatibility stored as list of strings
            if (compatibility) {
                payload.compatibility = compatibility.split(',').map(c => c.trim()).filter(c => c);
            }

            if (description) payload.description = description;
            if (manufacturer) payload.manufacturer = manufacturer;
            if (datasheetUrl) payload.datasheet_url = datasheetUrl;
            if (vendorUrl) payload.vendor_url = vendorUrl;

            // Merge additional specs
            if (Object.keys(additionalSpecs).length > 0) {
                payload.specifications = { ...additionalSpecs };
            }

            const response = await axios.patch(
                `${API_URL}/api/v1/global-catalog/enrich/${product.id}`,
                payload,
                { headers }
            );

            setSuccess('Product enriched successfully!');

            if (onEnriched) {
                onEnriched(response.data);
            }

            // Close after short delay to show success
            setTimeout(() => {
                onClose();
            }, 1500);

        } catch (err: any) {
            logger.error('Error enriching product:', err);
            setError(err.response?.data?.detail || 'Failed to enrich product');
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen || !product) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-xl font-bold text-primary">Enrich Product</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {product.vendor} - {product.sku || product.vendor_product_id}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 flex-1 overflow-y-auto">
                    {/* Product name display */}
                    <div className="mb-6 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg flex justify-between items-start gap-3">
                        <p className="font-medium text-gray-900 dark:text-white">
                            {product.name || product.product_name || 'Unknown Product'}
                        </p>
                        {product.vendor_url && (
                            <a
                                href={product.vendor_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="shrink-0 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm flex items-center gap-1"
                                title="Open vendor page in new tab"
                            >
                                <span>View Site</span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                        )}
                    </div>

                    {/* Error/Success Messages */}
                    {error && (
                        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200 rounded text-sm">
                            {error}
                        </div>
                    )}
                    {success && (
                        <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-200 rounded text-sm">
                            {success}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        {/* Price */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Price (USD)
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={priceUsd}
                                onChange={(e) => setPriceUsd(e.target.value)}
                                placeholder="e.g., 225.00"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>

                        {/* Manufacturer */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Manufacturer
                            </label>
                            <input
                                type="text"
                                value={manufacturer}
                                onChange={(e) => setManufacturer(e.target.value)}
                                placeholder="e.g., HPC Optics"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>

                        {/* Stock Status */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Stock Status
                            </label>
                            <input
                                type="text"
                                value={stockStatus}
                                onChange={(e) => setStockStatus(e.target.value)}
                                placeholder="e.g., In Stock, 14 left"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>

                        {/* Lead Time */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Lead Time
                            </label>
                            <input
                                type="text"
                                value={leadTime}
                                onChange={(e) => setLeadTime(e.target.value)}
                                placeholder="e.g., Ships Jan 3, 2-3 weeks"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>
                    </div>

                    {/* Compatibility */}
                    <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Compatible With (comma-separated)
                        </label>
                        <input
                            type="text"
                            value={compatibility}
                            onChange={(e) => setCompatibility(e.target.value)}
                            placeholder="e.g., Cisco QSFP-40G-LR4-S, Arista 7260QX, Intel X710"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Enter manufacturer part numbers this product is compatible with
                        </p>
                    </div>

                    {/* Description */}
                    <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Description
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Product description..."
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                    </div>

                    {/* URLs */}
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Datasheet URL
                            </label>
                            <input
                                type="url"
                                value={datasheetUrl}
                                onChange={(e) => setDatasheetUrl(e.target.value)}
                                placeholder="https://..."
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Vendor URL
                            </label>
                            <input
                                type="url"
                                value={vendorUrl}
                                onChange={(e) => setVendorUrl(e.target.value)}
                                placeholder="https://..."
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            />
                        </div>
                    </div>

                    {/* Additional Specifications */}
                    <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Additional Specifications
                        </label>

                        {/* Existing specs from product */}
                        {product.specifications && Object.keys(product.specifications).length > 0 && (
                            <div className="mb-2 p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs">
                                <p className="text-gray-500 mb-1">Existing specs:</p>
                                {Object.entries(product.specifications)
                                    .filter(([key]) => key !== 'stock_status' && key !== 'lead_time')
                                    .map(([key, val]) => (
                                        <span key={key} className="inline-block mr-2 mb-1 px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded">
                                            {key}: {String(val)}
                                        </span>
                                    ))
                                }
                            </div>
                        )}

                        {/* Added specs */}
                        {Object.keys(additionalSpecs).length > 0 && (
                            <div className="mb-2 flex flex-wrap gap-2">
                                {Object.entries(additionalSpecs).map(([key, val]) => (
                                    <span
                                        key={key}
                                        className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-sm"
                                    >
                                        {key}: {val}
                                        <button
                                            onClick={() => handleRemoveSpec(key)}
                                            className="text-blue-500 hover:text-blue-700"
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Add new spec */}
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={newSpecKey}
                                onChange={(e) => setNewSpecKey(e.target.value)}
                                placeholder="Key (e.g., wavelength)"
                                className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                            />
                            <input
                                type="text"
                                value={newSpecValue}
                                onChange={(e) => setNewSpecValue(e.target.value)}
                                placeholder="Value (e.g., 1310nm)"
                                className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                            />
                            <button
                                onClick={handleAddSpec}
                                disabled={!newSpecKey.trim() || !newSpecValue.trim()}
                                className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 text-sm"
                            >
                                Add
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {saving ? (
                            <>
                                <span className="animate-spin">⏳</span>
                                Saving...
                            </>
                        ) : (
                            <>
                                💾 Save Enrichment
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EnrichProductModal;
