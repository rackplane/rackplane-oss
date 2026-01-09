import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useCart } from '../contexts/CartContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import { useCapabilities } from '../contexts/CapabilityContext';
import { FEATURE_MESSAGES } from '../constants/featureMessages';
import EnrichProductModal, { EnrichProductModalProps } from './EnrichProductModal';

type EnrichableProduct = EnrichProductModalProps['product'];

interface ProductSearchModalProps {
    isOpen: boolean;
    onClose: () => void;
    onImport: (product: any, autoAdd?: boolean) => Promise<any>;
}

const ProductSearchModal: React.FC<ProductSearchModalProps> = ({ isOpen, onClose, onImport }) => {
    const { verticalPack } = useWhiteLabel();
    const { checkCapability } = useCapabilities();

    // Check capabilities once for reuse
    const hasVendorIntegrations = checkCapability('vendor_integrations');

    // Default vendor depends on vertical. Datacenter defaults to FS.com, others to All.
    const [vendor, setVendor] = useState(verticalPack === 'datacenter' ? 'FS.com' : 'All');
    const [searchTerm, setSearchTerm] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [importingId, setImportingId] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [totalCount, setTotalCount] = useState(0);
    const [liveSearching, setLiveSearching] = useState(false);
    const [liveSearchMessage, setLiveSearchMessage] = useState<string | null>(null);
    const { addToCart } = useCart();
    const [addingToCartId, setAddingToCartId] = useState<string | null>(null);
    const [enrichProduct, setEnrichProduct] = useState<EnrichableProduct | null>(null);
    const PAGE_SIZE = 10;

    // Update default vendor when vertical changes or modal opens
    useEffect(() => {
        if (isOpen) {
            setVendor(verticalPack === 'datacenter' ? 'FS.com' : 'All');
        }
    }, [isOpen, verticalPack]);

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(0); // Reset page on new search
            handleSearch(0);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchTerm, vendor]);

    // Handle page change directly
    const changePage = (newPage: number) => {
        setPage(newPage);
        handleSearch(newPage);
    };

    const handleSearch = async (targetPage = page) => {
        // if (!searchTerm.trim()) return; // Allow empty search to listing all

        setLoading(true);
        setError(null);

        try {
            const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };

            // All vendors search the local Global Catalog first (cached data from previous API lookups)
            // This includes FS.com, Mouser, and any other vendors whose data was cached
            {
                const offset = targetPage * PAGE_SIZE;
                const response = await axios.get(`${API_URL}/api/v1/fs/catalog/search`, {
                    params: {
                        q: searchTerm,
                        vendor: vendor === 'All' ? undefined : vendor,
                        limit: PAGE_SIZE,
                        offset: offset
                    },
                    headers
                });
                setResults(response.data.items);
                setTotalCount(response.data.count);
            }
        } catch (err: any) {
            logger.error('Error searching catalog:', err);
            setError(err.response?.data?.detail || 'Failed to search catalog.');
        } finally {
            setLoading(false);
        }
    };

    // Live search - fetches from vendor API and caches results
    const handleLiveSearch = async () => {
        if (!hasVendorIntegrations) {
            setError(FEATURE_MESSAGES.VENDOR_INTEGRATIONS);
            return;
        }

        if (!searchTerm.trim()) {
            setError('Enter a search term for live vendor search');
            return;
        }

        setLiveSearching(true);
        setLiveSearchMessage(null);
        setError(null);

        try {
            const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };

            if (vendor === 'Mouser') {
                // Call Mouser proxy to fetch and cache results
                const response = await axios.post(`${API_URL}/api/v1/mouser-proxy/search/keyword`, {
                    keyword: searchTerm,
                    records: 50,
                    startingRecord: 0,
                    searchOptions: 'None'
                }, { headers });

                const searchResults = response.data?.SearchResults || {};
                const resultCount = searchResults.NumberOfResult || 0;
                const parts = searchResults.Parts || [];

                // Transform Mouser results to match our catalog format
                const transformedResults = parts.map((part: any) => ({
                    vendor: 'Mouser',
                    vendor_product_id: part.MouserPartNumber,
                    sku: part.MouserPartNumber,
                    product_name: part.Description || part.ManufacturerPartNumber,
                    name: part.Description || part.ManufacturerPartNumber,
                    manufacturer: part.Manufacturer,
                    price_usd: part.PriceBreaks?.[0]?.Price ? parseFloat(part.PriceBreaks[0].Price.replace(/[^0-9.]/g, '')) : null,
                    category: part.Category,
                    datasheet_url: part.DataSheetUrl,
                    vendor_url: part.ProductDetailUrl,
                    image_url: part.ImagePath,
                    availability: part.Availability,
                    specs: part.ProductAttributes?.reduce((acc: any, attr: any) => {
                        acc[attr.AttributeName] = attr.AttributeValue;
                        return acc;
                    }, {}) || {}
                }));

                setResults(transformedResults);
                setTotalCount(resultCount);
                setPage(0);
                setLiveSearchMessage(`Found ${resultCount} results from Mouser (showing ${transformedResults.length})`);
            } else if (vendor === 'FS.com' || vendor === 'Amazon') {
                setError(`${vendor} does not have a live search API. Searching cached catalog...`);
                // Fallback to normal search effectively happens because the user hits "Live Search" 
                // but usually they just type and the debounced search runs handleSearch() which hits the cache.
                // But if they clicked the button, we should maybe trigger a cache search or just explain.
                // Actually, the button is conditional on vendor === 'Mouser' in the JSX (line 202), 
                // so the user can't click "Live Search" for Amazon/FS.com anyway.
                // This block is just defensive coding.
            } else {
                setError('Live search is only available for Mouser');
            }
        } catch (err: any) {
            logger.error('Error in live search:', err);
            setError(err.response?.data?.detail || 'Live search failed');
        } finally {
            setLiveSearching(false);
        }
    };

    const handleImportClick = async (product: any) => {
        setImportingId(product.vendor_product_id); // Or global ID if available
        try {
            // We pass the raw product data back up to the parent to handle the actual creation of the local VendorSKU
            // The parent (VendorSKUs.tsx) handles the POST /api/v1/vendor-skus/ logic
            await onImport(product);
            // Remove from list or show success state?
        } catch (err) {
            // Error handled by parent mostly, but we clear loading state here
        } finally {
            setImportingId(null);
        }
    };

    if (!isOpen) return null;

    const totalPages = Math.ceil(totalCount / PAGE_SIZE);

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <h2 className="text-xl font-bold text-primary">Search Global Catalog</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-6 flex-1 overflow-hidden flex flex-col">
                    <div className="flex gap-4 mb-4">
                        <div className="w-1/4">
                            <select
                                value={vendor}
                                onChange={(e) => setVendor(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                            >
                                {verticalPack === 'datacenter' && (
                                    <>
                                        <option value="FS.com">FS.com</option>
                                        <option value="Mouser">Mouser Electronics</option>
                                    </>
                                )}
                                {verticalPack === 'healthcare' && (
                                    <>
                                        {/* Future healthcare vendors */}
                                        {/* <option value="Medline">Medline</option> */}
                                    </>
                                )}
                                {verticalPack === 'warehouse' && (
                                    <>
                                        {/* Future warehouse vendors */}
                                        {/* <option value="Grainger">Grainger</option> */}
                                    </>
                                )}
                                <option value="Amazon">Amazon</option>
                                <option value="All">All Vendors (Global Catalog)</option>
                            </select>
                        </div>
                        <div className="flex-1">
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search by SKU, Name, or Specs..."
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                autoFocus
                            />
                        </div>
                        {/* Live Search Button - fetches from vendor API */}
                        {vendor === 'Mouser' && hasVendorIntegrations && (
                            <button
                                onClick={handleLiveSearch}
                                disabled={liveSearching || !searchTerm.trim()}
                                className={`px-4 py-2 rounded-md font-medium transition-colors ${liveSearching || !searchTerm.trim()
                                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700'
                                    }`}
                                title="Fetch fresh results from Mouser API (Premium feature)"
                            >
                                {liveSearching ? '🔄 Searching...' : '🔍 Search Live'}
                            </button>
                        )}
                    </div>

                    {/* Live search message */}
                    {liveSearchMessage && (
                        <div className="mb-2 p-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-200 rounded text-sm">
                            {liveSearchMessage}
                        </div>
                    )}

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200 rounded text-sm">
                            {error}
                        </div>
                    )}

                    <div className="flex-1 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                                <tr>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Vendor</th>
                                    <th className="p-3 text-sm font-semibold text-gray-900 dark:text-gray-100">SKU</th>
                                    <th className="p-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Product Name</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 w-24">Price</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 w-32">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                {loading ? (
                                    <tr>
                                        <td colSpan={5} className="p-8 text-center text-gray-500">Searching...</td>
                                    </tr>
                                ) : results.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="p-8 text-center text-gray-500">
                                            {loading ? "Searching..." : "No products found in Global Catalog. Import an FS order to populate."}
                                        </td>
                                    </tr>
                                ) : (
                                    results.map((item, idx) => {
                                        const isExpanded = expandedId === item.vendor_product_id;
                                        return (
                                            <React.Fragment key={idx}>
                                                <tr
                                                    className={`hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer ${isExpanded ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}
                                                    onClick={() => setExpandedId(isExpanded ? null : item.vendor_product_id)}
                                                >
                                                    <td className="p-3 text-sm text-gray-600 dark:text-gray-400">
                                                        <span className="mr-2">{isExpanded ? '▼' : '▶'}</span>
                                                        {item.vendor}
                                                    </td>
                                                    <td className="p-3 text-sm font-mono text-gray-900 dark:text-gray-100">{item.vendor_product_id}</td>
                                                    <td className="p-3 text-sm text-gray-900 dark:text-gray-100 font-medium">{item.product_name || item.name}</td>
                                                    <td className="p-3 text-sm text-gray-500 dark:text-gray-400">
                                                        {item.price_usd ? `$${item.price_usd.toFixed(2)}` : '-'}
                                                    </td>
                                                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                                                        <div className="flex flex-wrap gap-1">
                                                            <button
                                                                onClick={() => handleImportClick(item)}
                                                                disabled={importingId === item.vendor_product_id}
                                                                className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/60 text-xs font-medium disabled:opacity-50 whitespace-nowrap"
                                                                title="Add to your Vendor SKU list"
                                                            >
                                                                {importingId === item.vendor_product_id ? '...' : '+ Catalog'}
                                                            </button>
                                                            <button
                                                                onClick={async (e) => {
                                                                    e.stopPropagation();
                                                                    setAddingToCartId(item.vendor_product_id);
                                                                    try {
                                                                        await addToCart({ catalog_sku_id: item.id, quantity: 1 });
                                                                    } catch (err) {
                                                                        logger.error('Failed to add to cart:', err);
                                                                        alert('Failed to add to cart');
                                                                    } finally {
                                                                        setAddingToCartId(null);
                                                                    }
                                                                }}
                                                                disabled={addingToCartId === item.vendor_product_id}
                                                                className="px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs font-medium whitespace-nowrap"
                                                                title="Add to Shopping Cart"
                                                            >
                                                                {addingToCartId === item.vendor_product_id ? '🛒...' : '🛒 Cart'}
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setEnrichProduct(item);
                                                                }}
                                                                className="px-2 py-1 bg-amber-500 text-white rounded hover:bg-amber-600 text-xs font-medium whitespace-nowrap"
                                                                title="Enrich with price, stock, compatibility data"
                                                            >
                                                                ✏️ Enrich
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                                {
                                                    isExpanded && (
                                                        <tr className="bg-gray-50 dark:bg-gray-800/30">
                                                            <td colSpan={5} className="p-4">
                                                                <div className="grid grid-cols-2 gap-4 text-sm">
                                                                    {/* Left column - Details */}
                                                                    <div className="space-y-2">
                                                                        <div>
                                                                            <span className="font-semibold text-gray-700 dark:text-gray-300">Part Number:</span>
                                                                            <span className="ml-2 text-gray-600 dark:text-gray-400">{item.part_number || '-'}</span>
                                                                        </div>
                                                                        <div>
                                                                            <span className="font-semibold text-gray-700 dark:text-gray-300">Manufacturer:</span>
                                                                            <span className="ml-2 text-gray-600 dark:text-gray-400">{item.manufacturer || item.vendor}</span>
                                                                        </div>
                                                                        <div>
                                                                            <span className="font-semibold text-gray-700 dark:text-gray-300">Category:</span>
                                                                            <span className="ml-2 text-gray-600 dark:text-gray-400">{item.category || '-'}</span>
                                                                        </div>
                                                                        {item.specs && Object.keys(item.specs).length > 0 && (
                                                                            <div>
                                                                                <span className="font-semibold text-gray-700 dark:text-gray-300">Specifications:</span>
                                                                                <div className="mt-1 text-xs bg-white dark:bg-gray-900 p-2 rounded border border-gray-200 dark:border-gray-700">
                                                                                    {Object.entries(item.specs).map(([key, val]) => (
                                                                                        <div key={key} className="flex gap-2">
                                                                                            <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}:</span>
                                                                                            <span className="text-gray-700 dark:text-gray-300">{String(val)}</span>
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                    {/* Right column - Links */}
                                                                    <div className="space-y-3">
                                                                        {item.product_url && (
                                                                            <a
                                                                                href={item.product_url}
                                                                                target="_blank"
                                                                                rel="noopener noreferrer"
                                                                                className="flex items-center gap-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                                                                                onClick={(e) => e.stopPropagation()}
                                                                            >
                                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                                                </svg>
                                                                                <span>View on {item.vendor}</span>
                                                                            </a>
                                                                        )}
                                                                        {item.specs?.datasheet_url && (
                                                                            <a
                                                                                href={item.specs.datasheet_url}
                                                                                target="_blank"
                                                                                rel="noopener noreferrer"
                                                                                className="flex items-center gap-2 text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300"
                                                                                onClick={(e) => e.stopPropagation()}
                                                                            >
                                                                                <span>📄</span>
                                                                                <span>Download Datasheet</span>
                                                                            </a>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    )
                                                }
                                            </React.Fragment>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination Controls */}
                    <div className="mt-4 flex justify-between items-center border-t border-gray-200 dark:border-gray-700 pt-4">
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                            Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount} results
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => changePage(page - 1)}
                                disabled={page === 0 || loading}
                                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                            >
                                Previous
                            </button>
                            <span className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                                Page {page + 1} of {Math.max(1, totalPages)}
                            </span>
                            <button
                                onClick={() => changePage(page + 1)}
                                disabled={page >= totalPages - 1 || loading}
                                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Enrich Product Modal */}
            <EnrichProductModal
                isOpen={enrichProduct !== null}
                onClose={() => setEnrichProduct(null)}
                product={enrichProduct}
                onEnriched={(updated) => {
                    // Update the product in results with enriched data
                    setResults(prev => prev.map(p =>
                        p.id === updated.id ? { ...p, ...updated } : p
                    ));
                }}
            />
        </div >
    );
};

export default ProductSearchModal;
