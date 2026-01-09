// Custom hook to manage asset form state, validation, and submission
// Extracted from Assets.tsx for better separation of concerns

import { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import {
    Asset,
    AssetFormData,
    AssetType,
    Datacenter,
    Rack,
    Room,
    StorageContainer,
} from '../types/asset';
import { formatError } from '../utils/errorFormatters';

// Default empty form data
const getDefaultFormData = (): AssetFormData => ({
    asset_tag: '',
    serial_number: '',
    asset_type: '',
    manufacturer: '',
    model: '',
    status: 'received',
    on_loan: false,
    loan_direction: 'to_us',
    loan_party: '',
    loan_source: '',
    hostname: '',
    height_u: '',
    power_consumption_watts: '',
    description: '',
    sku: '',
    datacenter_id: '',
    rack_id: '',
    rack_position_start: '',
    storage_container_id: '',
    storage_location: '',
    container_id: '',
    min_stock_threshold: '',
    purchase_cost: '',
    purchase_date: '',
    currency: 'USD',
    supplier: '',
    po_number: '',
    warranty_start_date: '',
    warranty_end_date: '',
    cable_length: '',
    connector_type: '',
    quantity: '',
    fiber_type: '',
    fiber_connector_a: '',
    fiber_connector_b: '',
    fiber_breakout: '',
    dac_speed: '',
    dac_connector_a: '',
    dac_connector_b: '',
    dac_breakout: '',
    ethernet_category: '',
});
interface UseAssetFormProps {
    assets: Asset[];
    assetTypes: AssetType[];
    datacenters: Datacenter[];
    racks: Rack[];
    rooms: Room[];
    storageContainers: StorageContainer[];
    fetchAssets: () => Promise<void>;
}

interface UseAssetFormReturn {
    // Form state
    formData: AssetFormData;
    setFormData: React.Dispatch<React.SetStateAction<AssetFormData>>;
    editingAsset: Asset | null;
    setEditingAsset: React.Dispatch<React.SetStateAction<Asset | null>>;
    showModal: boolean;
    saving: boolean;
    error: string | null;
    setError: React.Dispatch<React.SetStateAction<string | null>>;

    // Image/OCR state
    uploadedImageUrl: string | null;
    setUploadedImageUrl: (url: string | null) => void;
    useManualSerial: boolean;
    setUseManualSerial: (value: boolean) => void;

    // SKU autocomplete state
    skuLookupLoading: boolean;
    skuLookupError: string | null;
    skuAutocompleteSuggestions: Array<{ sku: string; usage_count: number }>;
    showSkuAutocomplete: boolean;
    setShowSkuAutocomplete: (show: boolean) => void;

    // Modal handlers
    openAddModal: () => void;
    openEditModal: (asset: Asset) => void;
    closeModal: () => void;

    // Form handlers
    handleInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void;
    handleSubmit: (e: React.FormEvent) => Promise<void>;

    // OCR handlers
    handleOCRComplete: (ocrResult: any, imageUrl: string) => void;
    handleOCRClear: () => void;

    // SKU handlers
    handleSKULookup: (sku: string) => Promise<void>;
    fetchSkuAutocomplete: (query: string) => Promise<void>;
    handleSkuAutocompleteSelect: (sku: string) => void;

    // Helper
    shouldShowField: (fieldName: string) => boolean;
}

export const useAssetForm = ({
    assets,
    assetTypes,
    racks,
    rooms,
    storageContainers,
    fetchAssets,
}: UseAssetFormProps): UseAssetFormReturn => {
    // Form state
    const [formData, setFormData] = useState<AssetFormData>(getDefaultFormData());
    const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Image/OCR state
    const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
    const [useManualSerial, setUseManualSerial] = useState(false);

    // SKU autocomplete state
    const [skuLookupLoading, setSkuLookupLoading] = useState(false);
    const [skuLookupError, setSkuLookupError] = useState<string | null>(null);
    const [skuAutocompleteSuggestions, setSkuAutocompleteSuggestions] = useState<Array<{ sku: string; usage_count: number }>>([]);
    const [showSkuAutocomplete, setShowSkuAutocomplete] = useState(false);

    // Timeout refs for debouncing
    const skuLookupTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const skuAutocompleteTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // AbortController ref for cancelling in-flight requests (prevents race conditions)
    const skuAutocompleteAbortRef = useRef<AbortController | null>(null);

    // Cleanup timeouts and abort controllers on unmount
    useEffect(() => {
        return () => {
            if (skuLookupTimeoutRef.current) {
                clearTimeout(skuLookupTimeoutRef.current);
            }
            if (skuAutocompleteTimeoutRef.current) {
                clearTimeout(skuAutocompleteTimeoutRef.current);
            }
            if (skuAutocompleteAbortRef.current) {
                skuAutocompleteAbortRef.current.abort();
            }
        };
    }, []);

    // Helper function to determine which fields should be shown based on asset type
    const shouldShowField = useCallback((fieldName: string): boolean => {
        const assetType = formData.asset_type.toLowerCase();

        // Specific cable types have different field requirements
        const isDACCable = assetType === 'dac_cable';
        const isEthernetCable = assetType === 'ethernet_cable';
        const isElectricalCable = assetType === 'electrical_cable';
        const isFiberCable = assetType === 'fiber_cable';
        const isAnyCable = isDACCable || isEthernetCable || isElectricalCable || isFiberCable;
        const isPatchPanel = assetType === 'patch_panel';
        const isCopperTransceiver = assetType === 'copper_transceiver';
        const isOpticalTransceiver = assetType === 'optical_transceiver';
        const isAnyTransceiver = isCopperTransceiver || isOpticalTransceiver;

        // Check if asset type supports networking features
        const selectedAssetType = assetTypes.find((t: AssetType) =>
            t.name === formData.asset_type || t.display_name === formData.asset_type
        );
        const isNetworkable = selectedAssetType?.features?.networkable ?? false;

        switch (fieldName) {
            case 'asset_tag':
                return !(isAnyCable || isAnyTransceiver || isPatchPanel);

            case 'serial_number':
                return !(isAnyCable || isAnyTransceiver || isPatchPanel);

            case 'hostname':
                return isNetworkable && !(isAnyCable || isAnyTransceiver || isPatchPanel);

            case 'height_u':
                return isNetworkable && !(isAnyCable || isAnyTransceiver || isPatchPanel);

            default:
                return true;
        }
    }, [formData.asset_type, assetTypes]);

    // Open add modal with default form data
    const openAddModal = useCallback(() => {
        setEditingAsset(null);
        setFormData(getDefaultFormData());
        setError(null);
        setShowModal(true);
    }, []);

    // Open edit modal with asset data
    const openEditModal = useCallback((asset: Asset) => {
        setEditingAsset(asset);

        // Infer datacenter_id when editing
        let datacenterId = asset.datacenter_id?.toString() || '';
        if (!datacenterId && asset.rack_id) {
            const rack = racks.find(r => r.id === asset.rack_id);
            if (rack) {
                datacenterId = rack.datacenter_id.toString();
            }
        }
        if (!datacenterId && asset.storage_container_id) {
            const container = storageContainers.find(c => c.id === asset.storage_container_id);
            if (container) {
                if (container.datacenter_id) {
                    datacenterId = container.datacenter_id.toString();
                } else if (container.room_id) {
                    const room = rooms.find(r => r.id === container.room_id);
                    if (room) {
                        datacenterId = room.datacenter_id.toString();
                    }
                }
            }
        }

        const isCableType = ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
            .includes(asset.asset_type?.toLowerCase() || '');

        setFormData({
            asset_tag: asset.asset_tag,
            serial_number: asset.serial_number,
            asset_type: asset.asset_type,
            manufacturer: asset.manufacturer || '',
            model: asset.model || '',
            status: asset.status,
            on_loan: asset.on_loan || false,
            loan_direction: asset.loan_direction || 'to_us',
            loan_party: asset.loan_party || asset.loan_source || '',
            loan_source: asset.loan_source || '',
            hostname: asset.hostname || '',
            height_u: asset.height_u?.toString() || '',
            power_consumption_watts: asset.power_consumption_watts?.toString() || '',
            description: asset.description || '',
            sku: '',
            datacenter_id: datacenterId,
            rack_id: asset.rack_id?.toString() || '',
            rack_position_start: asset.rack_position_start?.toString() || '',
            storage_container_id: asset.storage_container_id?.toString() || '',
            storage_location: asset.storage_location || '',
            container_id: asset.container_id?.toString() || '',
            min_stock_threshold: isCableType ? '' : (asset.min_stock_threshold?.toString() || ''),
            purchase_cost: asset.purchase_cost?.toString() || '',
            purchase_date: asset.purchase_date?.split('T')[0] || '',
            currency: asset.currency || 'USD',
            supplier: asset.supplier || '',
            po_number: '',
            warranty_start_date: asset.warranty_start_date?.split('T')[0] || '',
            warranty_end_date: asset.warranty_end_date?.split('T')[0] || '',
            cable_length: asset.custom_fields?.cable_length || '',
            connector_type: asset.custom_fields?.connector_type || '',
            quantity: asset.custom_fields?.quantity?.toString() || '',
            fiber_type: asset.custom_fields?.fiber_type || '',
            fiber_connector_a: asset.custom_fields?.fiber_connector_a || asset.connector_type_end_a || '',
            fiber_connector_b: asset.custom_fields?.fiber_connector_b || asset.connector_type_end_b || '',
            fiber_breakout: asset.custom_fields?.fiber_breakout || '',
            dac_speed: asset.custom_fields?.dac_speed || '',
            dac_connector_a: asset.custom_fields?.dac_connector_a || asset.connector_type_end_a || '',
            dac_connector_b: asset.custom_fields?.dac_connector_b || asset.connector_type_end_b || '',
            dac_breakout: asset.custom_fields?.dac_breakout || '',
            ethernet_category: asset.custom_fields?.ethernet_category || asset.connector_type_end_a || '',
        });
        setError(null);
        setShowModal(true);
    }, [racks, rooms, storageContainers]);

    // Close modal and reset state
    const closeModal = useCallback(() => {
        setShowModal(false);
        setEditingAsset(null);
        setError(null);
        setUploadedImageUrl(null);
        setUseManualSerial(false);
    }, []);

    // Fetch SKU autocomplete suggestions with request cancellation
    const fetchSkuAutocomplete = useCallback(async (query: string) => {
        if (!query || query.trim().length < 1) {
            setSkuAutocompleteSuggestions([]);
            setShowSkuAutocomplete(false);
            return;
        }

        // Cancel any in-flight request to prevent race conditions
        if (skuAutocompleteAbortRef.current) {
            skuAutocompleteAbortRef.current.abort();
        }

        // Create new AbortController for this request
        const abortController = new AbortController();
        skuAutocompleteAbortRef.current = abortController;

        try {
            const response = await axios.get(`${API_URL}/api/v1/assets/skus/autocomplete`, {
                params: { q: query.trim(), limit: 10 },
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('auth_token')}`
                },
                signal: abortController.signal
            });

            if (response.data && response.data.skus) {
                setSkuAutocompleteSuggestions(response.data.skus);
                setShowSkuAutocomplete(true);
            }
        } catch (err: any) {
            // Ignore aborted requests - they're intentional
            if (axios.isCancel(err) || err.name === 'AbortError' || err.code === 'ERR_CANCELED') {
                return;
            }
            logger.debug('SKU autocomplete error:', err);
            setSkuAutocompleteSuggestions([]);
            setShowSkuAutocomplete(false);
        }
    }, []);

    // Handle SKU lookup from vendor catalog
    const handleSKULookup = useCallback(async (sku: string) => {
        if (!sku || sku.trim().length < 3) {
            setSkuLookupError(null);
            return;
        }

        setSkuLookupLoading(true);
        setSkuLookupError(null);

        try {
            const response = await axios.get(`${API_URL}/api/v1/vendor-skus/asset-data`, {
                params: { sku: sku.trim() },
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.data) {
                const assetData = response.data;
                setFormData(prev => ({
                    ...prev,
                    manufacturer: assetData.manufacturer || prev.manufacturer,
                    model: assetData.model || prev.model,
                    asset_type: assetData.asset_type || prev.asset_type,
                    sku: sku.trim(),
                    dac_speed: assetData.custom_fields?.dac_speed || assetData.custom_fields?.speed || prev.dac_speed,
                    dac_connector_a: assetData.custom_fields?.dac_connector_a || assetData.custom_fields?.connector_a || prev.dac_connector_a,
                    dac_connector_b: assetData.custom_fields?.dac_connector_b || assetData.custom_fields?.connector_b || prev.dac_connector_b,
                    dac_breakout: assetData.custom_fields?.dac_breakout || assetData.custom_fields?.breakout || prev.dac_breakout,
                    cable_length: assetData.custom_fields?.cable_length || assetData.custom_fields?.length || prev.cable_length,
                    connector_type: assetData.custom_fields?.connector_type || prev.connector_type,
                    fiber_type: assetData.custom_fields?.fiber_type || prev.fiber_type,
                    fiber_connector_a: assetData.custom_fields?.fiber_connector_a || prev.fiber_connector_a,
                    fiber_connector_b: assetData.custom_fields?.fiber_connector_b || prev.fiber_connector_b,
                    purchase_cost: assetData.purchase_cost?.toString() || prev.purchase_cost,
                    currency: assetData.currency || prev.currency,
                }));
            }
        } catch (err: any) {
            if (err.response?.status === 402) {
                setSkuLookupError('SKU lookup is a premium feature. Upgrade to access the SKU catalog.');
            } else if (err.response?.status === 404) {
                // SKU not found - not an error, just no data to populate
                setSkuLookupError(null);
            } else {
                setSkuLookupError('Error looking up SKU');
            }
        } finally {
            setSkuLookupLoading(false);
        }
    }, []);

    // Handle SKU autocomplete selection
    const handleSkuAutocompleteSelect = useCallback((sku: string) => {
        setFormData(prev => ({
            ...prev,
            sku: sku
        }));
        setShowSkuAutocomplete(false);
        if (sku.trim().length >= 3) {
            handleSKULookup(sku);
        }
    }, [handleSKULookup]);

    // Handle input change with SKU debouncing
    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value,
        }));

        // Auto-lookup SKU when user types (debounced)
        if (name === 'sku') {
            if (skuLookupTimeoutRef.current) {
                clearTimeout(skuLookupTimeoutRef.current);
            }
            if (skuAutocompleteTimeoutRef.current) {
                clearTimeout(skuAutocompleteTimeoutRef.current);
            }

            if (value.trim().length >= 1) {
                skuAutocompleteTimeoutRef.current = setTimeout(() => {
                    fetchSkuAutocomplete(value);
                }, 200);
            } else {
                setSkuAutocompleteSuggestions([]);
                setShowSkuAutocomplete(false);
            }

            if (value.trim().length >= 3) {
                skuLookupTimeoutRef.current = setTimeout(() => {
                    handleSKULookup(value);
                }, 500);
            } else {
                setSkuLookupError(null);
            }
        }
    }, [fetchSkuAutocomplete, handleSKULookup]);

    // Handle OCR complete
    const handleOCRComplete = useCallback((ocrResult: any, imageUrl: string) => {
        const parsed = ocrResult.parsed_data;

        setFormData(prev => ({
            ...prev,
            serial_number: parsed.serial_number || prev.serial_number,
            model: parsed.model || prev.model,
            manufacturer: parsed.manufacturer || prev.manufacturer,
            asset_tag: parsed.asset_tag || prev.asset_tag,
            hostname: parsed.hostname || prev.hostname,
        }));

        setUploadedImageUrl(imageUrl);
    }, []);

    // Handle OCR clear
    const handleOCRClear = useCallback(() => {
        setFormData(prev => ({
            ...prev,
            serial_number: '',
            model: '',
            manufacturer: '',
            asset_tag: '',
            hostname: '',
        }));
        setUploadedImageUrl(null);
    }, []);

    // Handle form submission
    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);

        try {
            // Validate asset_type is selected
            if (!formData.asset_type) {
                setError('Please select an asset type');
                setSaving(false);
                return;
            }

            // Verify the selected asset_type exists
            const selectedType = assetTypes.find((t: AssetType) => t.name === formData.asset_type);
            if (!selectedType) {
                setError(`Invalid asset type selected. Please refresh the page and try again.`);
                setSaving(false);
                return;
            }

            // Determine if auto-generation is needed
            const assetType = formData.asset_type.toLowerCase();
            const isCable = ['dac_cable', 'ethernet_cable', 'electrical_cable', 'fiber_cable'].includes(assetType);
            const isTransceiver = ['copper_transceiver', 'optical_transceiver'].includes(assetType);
            const isPatchPanel = assetType === 'patch_panel';
            const needsAutoGeneration = isCable || isTransceiver || isPatchPanel;

            // Auto-generate asset tag and serial number if needed
            let autoAssetTag = formData.asset_tag;
            let autoSerialNumber = formData.serial_number;

            if (needsAutoGeneration && !editingAsset && !useManualSerial) {
                try {
                    const serialResponse = await axios.post(`${API_URL}/api/v1/assets/generate-serial`, {
                        asset_type: formData.asset_type
                    }, {
                        headers: {
                            Authorization: `Bearer ${localStorage.getItem('auth_token')}`
                        }
                    });
                    autoAssetTag = serialResponse.data.asset_tag;
                    autoSerialNumber = serialResponse.data.serial_number;
                } catch (serialErr) {
                    logger.warn('Failed to generate serial from backend, using fallback:', serialErr);
                    autoAssetTag = `${assetType.toUpperCase()}-${Date.now()}`;
                    autoSerialNumber = `SN-${Date.now()}`;
                }
            }

            // Build custom_fields for cables and transceivers
            const customFields: any = {};

            if (assetType === 'fiber_cable') {
                if (formData.fiber_type) customFields.fiber_type = formData.fiber_type;
                if (formData.fiber_breakout) customFields.fiber_breakout = formData.fiber_breakout;
                if (formData.cable_length) customFields.cable_length = formData.cable_length;
                if (formData.quantity) customFields.quantity = parseInt(formData.quantity);
            } else if (assetType === 'dac_cable') {
                if (formData.dac_speed) customFields.dac_speed = formData.dac_speed;
                if (formData.dac_breakout) customFields.dac_breakout = formData.dac_breakout;
                if (formData.cable_length) customFields.cable_length = formData.cable_length;
                if (formData.quantity) customFields.quantity = parseInt(formData.quantity);
            } else if (isCable && formData.cable_length) {
                customFields.cable_length = formData.cable_length;
                if (formData.quantity) customFields.quantity = parseInt(formData.quantity);
            } else if (isTransceiver) {
                if (formData.connector_type) customFields.connector_type = formData.connector_type;
                if (formData.quantity) customFields.quantity = parseInt(formData.quantity);
            }

            // Build payload
            const payload: any = {
                asset_tag: shouldShowField('asset_tag') ? formData.asset_tag : autoAssetTag,
                serial_number: shouldShowField('serial_number') ? formData.serial_number : autoSerialNumber,
                asset_type: formData.asset_type,
                manufacturer: formData.manufacturer || null,
                model: formData.model || null,
                status: formData.status,
                on_loan: formData.on_loan,
                loan_direction: formData.on_loan ? formData.loan_direction : null,
                loan_party: formData.on_loan ? (formData.loan_party || null) : null,
                loan_source: formData.loan_source || null,
                hostname: shouldShowField('hostname') ? (formData.hostname || null) : null,
                height_u: shouldShowField('height_u') ? (formData.height_u ? parseInt(formData.height_u) : null) : null,
                power_consumption_watts: formData.power_consumption_watts ? parseFloat(formData.power_consumption_watts) : null,
                description: formData.description || null,
                sku: formData.sku || null,
                datacenter_id: formData.datacenter_id ? parseInt(formData.datacenter_id) : null,
                rack_id: formData.rack_id ? parseInt(formData.rack_id) : null,
                rack_position_start: formData.rack_id && formData.rack_position_start ? parseInt(formData.rack_position_start) : null,
                rack_position_end: formData.rack_id && formData.rack_position_start && formData.height_u
                    ? parseInt(formData.rack_position_start) + parseInt(formData.height_u) - 1
                    : null,
                storage_container_id: formData.storage_container_id ? parseInt(formData.storage_container_id) : null,
                storage_location: formData.storage_location || null,
                container_id: formData.container_id ? parseInt(formData.container_id) : null,
                min_stock_threshold: (['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable'].includes(formData.asset_type?.toLowerCase() || ''))
                    ? null
                    : (formData.min_stock_threshold ? parseInt(formData.min_stock_threshold) : null),
                purchase_cost: formData.purchase_cost ? parseFloat(formData.purchase_cost) : null,
                purchase_date: formData.purchase_date ? new Date(formData.purchase_date).toISOString() : null,
                currency: formData.currency || 'USD',
                supplier: formData.supplier || null,
                warranty_start_date: formData.warranty_start_date ? new Date(formData.warranty_start_date).toISOString() : null,
                warranty_end_date: formData.warranty_end_date ? new Date(formData.warranty_end_date).toISOString() : null,
                po_number: formData.po_number || null,
                connector_type_end_a: (
                    formData.dac_connector_a ||
                    formData.fiber_connector_a ||
                    formData.ethernet_category ||
                    null
                ),
                connector_type_end_b: (
                    formData.dac_connector_b ||
                    formData.fiber_connector_b ||
                    formData.ethernet_category ||
                    null
                ),
                custom_fields: Object.keys(customFields).length > 0 ? customFields : {},
                photo_urls: uploadedImageUrl ? [uploadedImageUrl] : [],
            };

            if (editingAsset) {
                await axios.put(`${API_URL}/api/v1/assets/${editingAsset.id}`, payload);
            } else {
                await axios.post(`${API_URL}/api/v1/assets/`, payload);
            }

            await fetchAssets();
            closeModal();
        } catch (err: any) {
            logger.error('Error saving asset:', err);
            const errorDetail = err.response?.data?.detail || 'Failed to save asset';
            setError(formatError(errorDetail));
        } finally {
            setSaving(false);
        }
    }, [formData, editingAsset, assetTypes, useManualSerial, uploadedImageUrl, shouldShowField, fetchAssets, closeModal]);

    return {
        // Form state
        formData,
        setFormData,
        editingAsset,
        setEditingAsset,
        showModal,
        saving,
        error,
        setError,

        // Image/OCR state
        uploadedImageUrl,
        setUploadedImageUrl,
        useManualSerial,
        setUseManualSerial,

        // SKU autocomplete state
        skuLookupLoading,
        skuLookupError,
        skuAutocompleteSuggestions,
        showSkuAutocomplete,
        setShowSkuAutocomplete,

        // Modal handlers
        openAddModal,
        openEditModal,
        closeModal,

        // Form handlers
        handleInputChange,
        handleSubmit,

        // OCR handlers
        handleOCRComplete,
        handleOCRClear,

        // SKU handlers
        handleSKULookup,
        fetchSkuAutocomplete,
        handleSkuAutocompleteSelect,

        // Helper
        shouldShowField,
    };
};
