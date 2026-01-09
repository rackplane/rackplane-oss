// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useNavigate } from 'react-router-dom';
import logger from '../utils/logger';
import { formatAssetType } from '../utils/formatAssetType';

interface SearchResult {
  query: string;
  total_results: number;
  assets: Array<{
    id: number;
    asset_tag: string;
    serial_number: string;
    asset_type: string;
    manufacturer: string;
    model: string;
    status: string;
    entity_type: string;
  }>;
  datacenters: Array<{
    id: number;
    name: string;
    code: string;
    address: string;
    entity_type: string;
  }>;
  rooms: Array<{
    id: number;
    name: string;
    code: string;
    datacenter_id: number;
    entity_type: string;
  }>;
  racks: Array<{
    id: number;
    name: string;
    code: string;
    datacenter_id: number;
    room_id: number;
    entity_type: string;
  }>;
  network_cables: Array<{
    id: number;
    name: string;
    cable_type: string;
    speed: string;
    entity_type: string;
  }>;
  power_cables: Array<{
    id: number;
    name: string;
    voltage: string;
    connector_end_a: string;
    connector_end_b: string;
    entity_type: string;
  }>;
  asset_types: Array<{
    id: number;
    name: string;
    display_name: string;
    description: string;
    entity_type: string;
  }>;
  storage_containers?: Array<{
    id: number;
    name: string;
    container_type: string;
    location?: string;
    description?: string;
    rack?: {
      id: number;
      name: string;
      code: string;
    };
    entity_type: string;
  }>;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

const GlobalSearch: React.FC<GlobalSearchProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    // Clear previous timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // If query is empty, clear results
    if (!query.trim()) {
      setResults(null);
      setLoading(false);
      return;
    }

    // Set loading state
    setLoading(true);

    // Create new timer for debounced search
    const timer = setTimeout(() => {
      performSearch(query.trim());
    }, 300); // 300ms debounce

    setDebounceTimer(timer);

    // Cleanup
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [query]);

  const performSearch = async (searchQuery: string) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/search/`, {
        params: { q: searchQuery, limit: 20 }
      });
      setResults(response.data);
    } catch (error) {
      logger.error('Error performing search:', error);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleResultClick = (entityType: string, id: number, additionalData?: any) => {
    switch (entityType) {
      case 'asset':
        navigate(`/assets/${id}`);
        break;
      case 'datacenter':
        navigate(`/locations`);
        break;
      case 'room':
        navigate(`/locations`);
        break;
      case 'rack':
        navigate(`/racks/${id}`);
        break;
      case 'storage_container':
        navigate(`/storage-containers/${id}`);
        break;
      case 'network_cable':
      case 'power_cable':
        // Navigate to connections or appropriate page
        navigate(`/connections`);
        break;
      case 'asset_type':
        navigate(`/asset-types`);
        break;
      default:
        break;
    }
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center pt-20" onClick={onClose}>
      <div className="bg-card rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Search Input */}
        <div className="p-4 border-b">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search assets, locations, cables, types..."
              className="w-full px-4 py-3 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <svg
              className="absolute left-3 top-3.5 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {loading && (
              <div className="absolute right-3 top-3.5">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {!query.trim() && (
            <div className="text-center text-gray-500 py-8">
              Start typing to search across assets, locations, cables, and more...
            </div>
          )}

          {query.trim() && !loading && results && results.total_results === 0 && (
            <div className="text-center text-gray-500 py-8">
              No results found for "{query}"
            </div>
          )}

          {results && results.total_results > 0 && (
            <div className="space-y-6">
              {/* Assets */}
              {results.assets.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Assets ({results.assets.length})
                  </h3>
                  <div className="space-y-1">
                    {results.assets.map((asset) => (
                      <button
                        key={asset.id}
                        onClick={() => handleResultClick('asset', asset.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{asset.asset_tag}</div>
                        <div className="text-sm text-gray-600">
                          {asset.manufacturer} {asset.model} • {formatAssetType(asset.asset_type)}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Datacenters */}
              {results.datacenters.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Datacenters ({results.datacenters.length})
                  </h3>
                  <div className="space-y-1">
                    {results.datacenters.map((dc) => (
                      <button
                        key={dc.id}
                        onClick={() => handleResultClick('datacenter', dc.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{dc.name}</div>
                        <div className="text-sm text-gray-600">{dc.code} • {dc.address}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Rooms */}
              {results.rooms.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Rooms ({results.rooms.length})
                  </h3>
                  <div className="space-y-1">
                    {results.rooms.map((room) => (
                      <button
                        key={room.id}
                        onClick={() => handleResultClick('room', room.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{room.name}</div>
                        <div className="text-sm text-gray-600">{room.code}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Racks */}
              {results.racks.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Racks ({results.racks.length})
                  </h3>
                  <div className="space-y-1">
                    {results.racks.map((rack) => (
                      <button
                        key={rack.id}
                        onClick={() => handleResultClick('rack', rack.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{rack.name}</div>
                        <div className="text-sm text-gray-600">{rack.code}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Storage Containers */}
              {results.storage_containers && results.storage_containers.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Storage Containers ({results.storage_containers.length})
                  </h3>
                  <div className="space-y-1">
                    {results.storage_containers.map((container) => (
                      <button
                        key={container.id}
                        onClick={() => handleResultClick('storage_container', container.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{container.name}</div>
                        <div className="text-sm text-gray-600">
                          {container.container_type}
                          {container.location && ` • ${container.location}`}
                          {container.rack && ` • Rack: ${container.rack.name}`}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Network Cables */}
              {results.network_cables.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Network Cables ({results.network_cables.length})
                  </h3>
                  <div className="space-y-1">
                    {results.network_cables.map((cable) => (
                      <button
                        key={cable.id}
                        onClick={() => handleResultClick('network_cable', cable.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{cable.name}</div>
                        <div className="text-sm text-gray-600">{cable.cable_type} • {cable.speed}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Power Cables */}
              {results.power_cables.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Power Cables ({results.power_cables.length})
                  </h3>
                  <div className="space-y-1">
                    {results.power_cables.map((cable) => (
                      <button
                        key={cable.id}
                        onClick={() => handleResultClick('power_cable', cable.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{cable.name}</div>
                        <div className="text-sm text-gray-600">{cable.voltage} • {cable.connector_end_a}-{cable.connector_end_b}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Asset Types */}
              {results.asset_types.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                    Asset Types ({results.asset_types.length})
                  </h3>
                  <div className="space-y-1">
                    {results.asset_types.map((type) => (
                      <button
                        key={type.id}
                        onClick={() => handleResultClick('asset_type', type.id)}
                        className="w-full text-left px-3 py-2 hover:bg-table-row-hover rounded transition"
                      >
                        <div className="font-medium text-gray-900">{type.display_name}</div>
                        <div className="text-sm text-gray-600">{type.description || type.name}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GlobalSearch;

