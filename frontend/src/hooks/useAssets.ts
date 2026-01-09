// Custom hook for fetching asset-related data
// Extracted from Assets.tsx for reusability

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import {
    Asset,
    AssetType,
    Datacenter,
    Rack,
    Room,
    StorageContainer,
    PortTemplate,
} from '../types/asset';
import logger from '../utils/logger';

interface UseAssetsOptions {
    autoFetch?: boolean;
}

interface UseAssetsReturn {
    assets: Asset[];
    loading: boolean;
    error: string | null;
    refetch: (searchTerm?: string) => Promise<void>;
}

export function useAssets(options: UseAssetsOptions = {}): UseAssetsReturn {
    const { autoFetch = true } = options;
    const [assets, setAssets] = useState<Asset[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAssets = useCallback(async (searchTerm: string = '') => {
        setLoading(true);
        setError(null);
        try {
            const params: any = { limit: 10000 };
            if (searchTerm) {
                params.search = searchTerm;
            }
            const response = await axios.get(`${API_URL}/api/v1/assets/`, { params });
            setAssets(response.data.assets || []);
        } catch (err) {
            logger.error('Error fetching assets:', err);
            setError('Failed to fetch assets');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (autoFetch) {
            fetchAssets();
        }
    }, [autoFetch, fetchAssets]);

    return { assets, loading, error, refetch: fetchAssets };
}

interface UseAssetTypesReturn {
    assetTypes: AssetType[];
    loading: boolean;
    refetch: () => Promise<void>;
}

export function useAssetTypes(): UseAssetTypesReturn {
    const [assetTypes, setAssetTypes] = useState<AssetType[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchAssetTypes = useCallback(async () => {
        try {
            const response = await axios.get(`${API_URL}/api/v1/asset-types/`);
            setAssetTypes(response.data || []);
        } catch (error) {
            logger.error('Error fetching asset types:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAssetTypes();
    }, [fetchAssetTypes]);

    return { assetTypes, loading, refetch: fetchAssetTypes };
}

interface UseLocationsReturn {
    datacenters: Datacenter[];
    racks: Rack[];
    rooms: Room[];
    storageContainers: StorageContainer[];
    loading: boolean;
    refetch: () => Promise<void>;
}

export function useLocations(): UseLocationsReturn {
    const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
    const [racks, setRacks] = useState<Rack[]>([]);
    const [rooms, setRooms] = useState<Room[]>([]);
    const [storageContainers, setStorageContainers] = useState<StorageContainer[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchAll = useCallback(async () => {
        try {
            const [dcRes, rackRes, roomRes, containerRes] = await Promise.all([
                axios.get(`${API_URL}/api/v1/locations/datacenters`),
                axios.get(`${API_URL}/api/v1/locations/racks`),
                axios.get(`${API_URL}/api/v1/locations/rooms`),
                axios.get(`${API_URL}/api/v1/storage-containers/`),
            ]);
            setDatacenters(dcRes.data || []);
            setRacks(rackRes.data || []);
            setRooms(roomRes.data || []);
            setStorageContainers(containerRes.data || []);
        } catch (error) {
            logger.error('Error fetching locations:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    return { datacenters, racks, rooms, storageContainers, loading, refetch: fetchAll };
}

interface UsePortTemplatesReturn {
    portTemplates: PortTemplate[];
    loading: boolean;
    refetch: () => Promise<void>;
}

export function usePortTemplates(): UsePortTemplatesReturn {
    const [portTemplates, setPortTemplates] = useState<PortTemplate[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchPortTemplates = useCallback(async () => {
        try {
            const response = await axios.get(`${API_URL}/api/v1/port-templates/`);
            setPortTemplates(response.data || []);
        } catch (error) {
            logger.error('Error fetching port templates:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPortTemplates();
    }, [fetchPortTemplates]);

    return { portTemplates, loading, refetch: fetchPortTemplates };
}
