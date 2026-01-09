// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useCapabilities } from '../contexts/CapabilityContext';

interface VendorSKU {
  id: number;
  vendor: string;
  sku: string;
  name: string;
  manufacturer?: string;
  asset_type?: string;
  specifications?: Record<string, any>;
  price_usd?: number;
  currency: string;
  compatibility?: Record<string, any>;
  description?: string;
  vendor_url?: string;
}

interface SKUMatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSKU: (sku: VendorSKU) => void;
  detectedText: string;
  imageUrl?: string;
}

const SKUMatchModal: React.FC<SKUMatchModalProps> = ({
  isOpen,
  onClose,
  onSelectSKU,
  detectedText,
  imageUrl
}) => {
  const [searching, setSearching] = useState(false);
  const [matchedSKU, setMatchedSKU] = useState<VendorSKU | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [potentialSKUs, setPotentialSKUs] = useState<string[]>([]);
  const { checkCapability } = useCapabilities();

  useEffect(() => {
    if (isOpen && detectedText) {
      searchForSKU();
    } else {
      setMatchedSKU(null);
      setSearchError(null);
      setPotentialSKUs([]);
    }
  }, [isOpen, detectedText]);

  const extractPotentialSKUs = (text: string): string[] => {
    const skus: string[] = [];

    // Look for FS.com SKU patterns:
    // - 6-digit numbers (common FS.com SKU format)
    // - "SKU: 123456" or "SKU:123456"
    // - URLs like "fs.com/products/123456.html"
    // - Part numbers that might be SKUs

    // Extract 6-digit numbers (likely SKUs)
    const sixDigitPattern = /\b\d{6}\b/g;
    const matches = text.match(sixDigitPattern);
    if (matches) {
      skus.push(...matches);
    }

    // Extract from "SKU: 123456" pattern
    const skuPattern = /SKU[:\s]+(\d{5,7})/gi;
    let skuMatch;
    while ((skuMatch = skuPattern.exec(text)) !== null) {
      if (skuMatch[1]) skus.push(skuMatch[1]);
    }

    // Extract from FS.com URLs
    const urlPattern = /fs\.com\/products\/(\d+)/gi;
    let urlMatch;
    while ((urlMatch = urlPattern.exec(text)) !== null) {
      if (urlMatch[1]) skus.push(urlMatch[1]);
    }

    // Remove duplicates
    return Array.from(new Set(skus));
  };





  const searchForSKU = async () => {
    if (!detectedText) return;

    if (!checkCapability('sku_lookup')) {
      setSearchError('SKU Catalog is a premium feature. Upgrade your subscription to access SKU matching.');
      return;
    }

    setSearching(true);
    setSearchError(null);
    setMatchedSKU(null);

    try {
      // Extract potential SKUs from the text
      const potentialSKUs = extractPotentialSKUs(detectedText);
      setPotentialSKUs(potentialSKUs);

      if (potentialSKUs.length === 0) {
        setSearchError('No SKU patterns found in scanned text');
        setSearching(false);
        return;
      }

      // First, try text matching (more flexible, works with any vendor)
      try {
        const matchResponse = await axios.get(
          `${API_URL}/api/v1/vendor-skus/match-from-text`,
          {
            params: { text: detectedText },
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token') || localStorage.getItem('token')}`
            }
          }
        );

        if (matchResponse.data) {
          setMatchedSKU(matchResponse.data);
          setSearching(false);
          return;
        }
      } catch (err: any) {
        // Text matching failed, try individual SKU lookups
        // 402 handled by capability check, but keeping fallback
        if (err.response?.status === 402) {
          setSearchError('SKU Catalog is a premium feature. Upgrade your subscription to access SKU matching.');
          setSearching(false);
          return;
        } else if (err.response?.status !== 404) {
          logger.error('Error matching SKU from text:', err);
        }
      }

      // If text matching didn't work, try exact SKU lookups for each potential SKU
      for (const sku of potentialSKUs) {
        try {
          const lookupResponse = await axios.get(
            `${API_URL}/api/v1/vendor-skus/lookup`,
            {
              params: { sku },
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token') || localStorage.getItem('token')}`
              }
            }
          );

          if (lookupResponse.data) {
            setMatchedSKU(lookupResponse.data);
            setSearching(false);
            return;
          }
        } catch (err: any) {
          // SKU not found, try next one
          if (err.response?.status === 402) {
            setSearchError('SKU Catalog is a premium feature. Upgrade your subscription to access SKU matching.');
            setSearching(false);
            return;
          } else if (err.response?.status !== 404) {
            logger.error('Error looking up SKU:', err);
          }
        }
      }

      // No matches found
      if (potentialSKUs.length > 0) {
        setSearchError(`Found potential SKUs (${potentialSKUs.join(', ')}) but none matched in catalog. Add them to the catalog first.`);
      } else {
        setSearchError('No SKU patterns detected in the scanned text.');
      }
    } catch (err: any) {
      setSearchError('Error searching for SKU');
      logger.error('Error in SKU search:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleUseSKU = () => {
    if (matchedSKU) {
      onSelectSKU(matchedSKU);
      onClose();
    }
  };

  const handleAddToCatalog = () => {
    // Open FS.com product page if we have a potential SKU
    if (potentialSKUs.length > 0) {
      const sku = potentialSKUs[0];
      window.open(`https://www.fs.com/products/${sku}.html`, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
              🔍 SKU Catalog Match
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 text-2xl"
            >
              &times;
            </button>
          </div>

          {/* Image Preview */}
          {imageUrl && (
            <div className="mb-4">
              <img
                src={imageUrl}
                alt="Scanned label"
                className="max-w-full h-auto rounded border border-gray-300 dark:border-gray-600"
              />
            </div>
          )}

          {/* Detected Text */}
          <div className="mb-4 p-3 bg-subtle-card rounded">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Detected Text:</p>
            <p className="text-sm font-mono text-gray-800 dark:text-gray-200 break-all">
              {detectedText}
            </p>
          </div>

          {/* Searching State */}
          {searching && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">Searching for matching SKU...</p>
            </div>
          )}

          {/* Matched SKU */}
          {matchedSKU && !searching && (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded">
                <p className="text-green-800 dark:text-green-200 font-semibold mb-2">
                  ✅ Found Matching Product!
                </p>
                <div className="space-y-2">
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">SKU:</span>
                    <span className="ml-2 text-gray-800 dark:text-gray-200">{matchedSKU.sku}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Name:</span>
                    <span className="ml-2 text-gray-800 dark:text-gray-200">{matchedSKU.name}</span>
                  </div>
                  {matchedSKU.price_usd && (
                    <div>
                      <span className="font-semibold text-gray-700 dark:text-gray-300">Price:</span>
                      <span className="ml-2 text-gray-800 dark:text-gray-200">
                        ${matchedSKU.price_usd} {matchedSKU.currency}
                      </span>
                    </div>
                  )}
                  {matchedSKU.specifications && (
                    <div className="mt-2">
                      <span className="font-semibold text-gray-700 dark:text-gray-300">Specs:</span>
                      <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        {matchedSKU.specifications.speed && (
                          <div>Speed: {matchedSKU.specifications.speed}</div>
                        )}
                        {matchedSKU.specifications.length && (
                          <div>Length: {matchedSKU.specifications.length}</div>
                        )}
                        {matchedSKU.specifications.connector_a && (
                          <div>Connector: {matchedSKU.specifications.connector_a} → {matchedSKU.specifications.connector_b || 'N/A'}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleUseSKU}
                  className="flex-1 bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-lg font-semibold"
                >
                  Use This Product
                </button>
                {matchedSKU.vendor_url && (
                  <a
                    href={matchedSKU.vendor_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    View on FS.com
                  </a>
                )}
              </div>
            </div>
          )}

          {/* No Match Found */}
          {!matchedSKU && !searching && potentialSKUs.length > 0 && (
            <div className="space-y-4">
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-700 rounded">
                <p className="text-yellow-800 dark:text-yellow-200 font-semibold mb-2">
                  ⚠️ Potential SKU Found
                </p>
                <p className="text-yellow-700 dark:text-yellow-300 text-sm mb-2">
                  Found potential SKU(s): <strong>{potentialSKUs.join(', ')}</strong>
                </p>
                <p className="text-yellow-700 dark:text-yellow-300 text-sm">
                  This SKU is not in your catalog yet. Add it to enable auto-population.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    // Navigate to vendor SKU catalog to add the SKU
                    window.location.href = '/vendor-skus';
                  }}
                  className="flex-1 bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-lg font-semibold"
                >
                  Add to Catalog
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* Error State */}
          {searchError && !searching && (
            <div className="p-4 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded">
              <p className="text-red-800 dark:text-red-200">{searchError}</p>
            </div>
          )}

          {/* No SKU Found */}
          {!matchedSKU && !searching && potentialSKUs.length === 0 && !searchError && (
            <div className="p-4 bg-subtle-card rounded">
              <p className="text-gray-600 dark:text-gray-400">
                No SKU patterns detected in the scanned text. Make sure the label is clear and contains a SKU number.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SKUMatchModal;

