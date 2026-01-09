// Custom hook to manage asset-related data fetching
// Consolidates all asset, asset type, location, and container data management

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import {
  Asset,
  AssetType,
  Datacenter,
  Rack,
  Room,
  StorageContainer,
  PortTemplate,
} from '../types/asset';

interface UseAssetDataReturn {
  // Data
  assets: Asset[];
  assetTypes: AssetType[];
  datacenters: Datacenter[];
  racks: Rack[];
  rooms: Room[];
  storageContainers: StorageContainer[];
  portTemplates: PortTemplate[];

  // Loading states
  loading: boolean;

  // Fetch functions
  fetchAssets: (searchTerm?: string) => Promise<void>;
  fetchAssetTypes: () => Promise<void>;
  fetchDatacenters: () => Promise<void>;
  fetchRacks: () => Promise<void>;
  fetchRooms: () => Promise<void>;
  fetchStorageContainers: () => Promise<void>;
  fetchPortTemplates: () => Promise<void>;

  // Setters (for external updates)
  setAssets: React.Dispatch<React.SetStateAction<Asset[]>>;
  setAssetTypes: React.Dispatch<React.SetStateAction<AssetType[]>>;
}

export const useAssetData = (): UseAssetDataReturn => {
  // State
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [racks, setRacks] = useState<Rack[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [storageContainers, setStorageContainers] = useState<StorageContainer[]>([]);
  const [portTemplates, setPortTemplates] = useState<PortTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch functions
  const fetchAssets = useCallback(async (searchTerm: string = '') => {
    setLoading(true);
    try {
      const params: any = { limit: 10000 };
      if (searchTerm) {
        params.search = searchTerm;
      }

      const response = await axios.get(`${API_URL}/api/v1/assets/`, { params });
      setAssets(response.data.assets || []);
    } catch (error) {
      logger.error('Error fetching assets:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAssetTypes = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/asset-types/`);
      const types = response.data || [];
      setAssetTypes(types);
    } catch (error) {
      logger.error('Error fetching asset types:', error);
    }
  }, []);

  const fetchDatacenters = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
    } catch (error) {
      logger.error('Error fetching datacenters:', error);
    }
  }, []);

  const fetchRacks = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`);
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching racks:', error);
    }
  }, []);

  const fetchRooms = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/rooms`);
      setRooms(response.data || []);
    } catch (error) {
      logger.error('Error fetching rooms:', error);
    }
  }, []);

  const fetchStorageContainers = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/storage-containers/`);
      setStorageContainers(response.data || []);
    } catch (error) {
      logger.error('Error fetching storage containers:', error);
    }
  }, []);

  const fetchPortTemplates = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/port-templates/`);
      setPortTemplates(response.data || []);
    } catch (error) {
      logger.error('Error fetching port templates:', error);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([
        fetchAssetTypes(),
        fetchDatacenters(),
        fetchRacks(),
        fetchRooms(),
        fetchStorageContainers(),
      ]);
      // Don't fetch assets here - let the search effect handle it
      setLoading(false);
    };

    loadInitialData();
  }, [fetchAssetTypes, fetchDatacenters, fetchRacks, fetchRooms, fetchStorageContainers]);

  return {
    // Data
    assets,
    assetTypes,
    datacenters,
    racks,
    rooms,
    storageContainers,
    portTemplates,

    // Loading state
    loading,

    // Fetch functions
    fetchAssets,
    fetchAssetTypes,
    fetchDatacenters,
    fetchRacks,
    fetchRooms,
    fetchStorageContainers,
    fetchPortTemplates,

    // Setters (for cases where parent needs to update directly)
    setAssets,
    setAssetTypes,
  };
};
