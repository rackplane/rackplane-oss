// Asset Bulk Edit Modal Component
// Extracted from Assets.tsx for better organization
// Handles bulk editing of multiple selected assets

import React from 'react';
import { AssetType, Datacenter, Rack, Room, StorageContainer, PortTemplate } from '../../types/asset';
import { FIBER_CONNECTOR_OPTIONS } from '../../constants/assetOptions';

// Bulk edit form data structure
export interface BulkEditData {
    datacenter_id: string;
    rack_id: string;
    storage_container_id: string;
    status: string;
    asset_type: string;
    // Cable connector end types
    dac_connector_a: string;
    dac_connector_b: string;
    // Fiber cable fields
    fiber_connector_a: string;
    fiber_connector_b: string;
    fiber_type: string;
    // Transceiver fields
    transceiver_type: string;
    fiber_connector: string;
    // Ethernet cable fields
    ethernet_category: string;
}

// Info about selected asset types for conditional rendering
export interface BulkEditAssetTypeInfo {
    allAreDACCables: boolean;
    allAreFiberCables: boolean;
    allAreTransceivers: boolean;
    allAreEthernetCables: boolean;
    allAreCables: boolean;
}

interface AssetBulkEditModalProps {
    // Modal state
    showBulkEditModal: boolean;
    closeBulkEditModal: () => void;
    selectedAssets: number[];

    // Form state
    error: string | null;
    saving: boolean;
    bulkEditData: BulkEditData;
    setBulkEditData: React.Dispatch<React.SetStateAction<BulkEditData>>;
    bulkEditAssetTypeInfo: BulkEditAssetTypeInfo;

    // Data lists
    assetTypes: AssetType[];
    datacenters: Datacenter[];
    racks: Rack[];
    rooms: Room[];
    storageContainers: StorageContainer[];

    // Port template state
    portTemplates: PortTemplate[];
    selectedTemplateId: number | null;
    setSelectedTemplateId: (id: number | null) => void;
    overwritePorts: boolean;
    setOverwritePorts: (value: boolean) => void;

    // Handlers
    handleBulkEdit: (e: React.FormEvent) => void;

    // Context
    t: (key: any) => string;
}

const AssetBulkEditModal: React.FC<AssetBulkEditModalProps> = ({
    showBulkEditModal,
    closeBulkEditModal,
    selectedAssets,
    error,
    saving,
    bulkEditData,
    setBulkEditData,
    bulkEditAssetTypeInfo,
    assetTypes,
    datacenters,
    racks,
    rooms,
    storageContainers,
    portTemplates,
    selectedTemplateId,
    setSelectedTemplateId,
    overwritePorts,
    setOverwritePorts,
    handleBulkEdit,
    t,
}) => {
    if (!showBulkEditModal) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-bold text-primary">
                            Edit {selectedAssets.length} Selected Assets
                        </h2>
                        <button
                            onClick={closeBulkEditModal}
                            className="text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-gray-300 text-2xl"
                        >
                            &times;
                        </button>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 rounded">
                            {error}
                        </div>
                    )}

                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        Only fill in the fields you want to update. Empty fields will remain unchanged.
                    </p>

                    <form onSubmit={handleBulkEdit}>
                        <div className="grid grid-cols-1 gap-4">
                            {/* Asset Type */}
                            <div>
                                <label className="block text-sm font-medium text-primary mb-2">
                                    Asset Type
                                </label>
                                <select
                                    value={bulkEditData.asset_type}
                                    onChange={(e) => setBulkEditData({ ...bulkEditData, asset_type: e.target.value })}
                                    className="input w-full"
                                >
                                    <option value="">-- No Change --</option>
                                    {assetTypes.map(type => (
                                        <option key={type.id} value={type.name}>
                                            {type.display_name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Status */}
                            <div>
                                <label className="block text-sm font-medium text-primary mb-2">
                                    Status
                                </label>
                                <select
                                    value={bulkEditData.status}
                                    onChange={(e) => setBulkEditData({ ...bulkEditData, status: e.target.value })}
                                    className="input w-full"
                                >
                                    <option value="">-- No Change --</option>
                                    <option value="ordered">Ordered</option>
                                    <option value="in_transit">In Transit</option>
                                    <option value="received">Received</option>
                                    <option value="staging">Staging</option>
                                    <option value="in_storage">In Storage</option>
                                    <option value="active">Active</option>
                                    <option value="deployed">Deployed</option>
                                    <option value="maintenance">Maintenance</option>
                                    <option value="failed">Failed</option>
                                    <option value="rma">RMA</option>
                                    <option value="retired">Retired</option>
                                    <option value="decommissioned">Decommissioned</option>
                                </select>
                            </div>

                            {/* Datacenter */}
                            <div>
                                <label className="block text-sm font-medium text-primary mb-2">
                                    {t('location')}
                                </label>
                                <select
                                    value={bulkEditData.datacenter_id}
                                    onChange={(e) => setBulkEditData({ ...bulkEditData, datacenter_id: e.target.value })}
                                    className="input w-full"
                                >
                                    <option value="">-- No Change --</option>
                                    {datacenters.map(dc => (
                                        <option key={dc.id} value={dc.id}>
                                            {dc.name} ({dc.code})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Location (Rack / Storage / Room) */}
                            <div>
                                <label className="block text-sm font-medium text-primary mb-2">
                                    Location
                                </label>
                                <select
                                    value={bulkEditData.rack_id}
                                    onChange={(e) => setBulkEditData({ ...bulkEditData, rack_id: e.target.value })}
                                    className="input w-full"
                                    disabled={!bulkEditData.datacenter_id}
                                >
                                    <option value="">-- No Change --</option>
                                    {racks
                                        .filter(rack => !bulkEditData.datacenter_id || rack.datacenter_id === parseInt(bulkEditData.datacenter_id))
                                        .map(rack => (
                                            <option key={rack.id} value={rack.id}>
                                                {rack.name}
                                            </option>
                                        ))}
                                </select>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {!bulkEditData.datacenter_id
                                        ? `Select a ${t('location').toLowerCase()} first`
                                        : `Optional - Set ${t('bin').toLowerCase()} for deployed ${t('items').toLowerCase()}; use ${t('container').toLowerCase()} for ${t('bins').toLowerCase()}`}
                                </p>
                            </div>

                            {/* Storage Container */}
                            <div>
                                <label className="block text-sm font-medium text-primary mb-2">
                                    Storage Container
                                </label>
                                <select
                                    value={bulkEditData.storage_container_id}
                                    onChange={(e) => setBulkEditData({ ...bulkEditData, storage_container_id: e.target.value })}
                                    className="input w-full"
                                    disabled={!bulkEditData.datacenter_id}
                                >
                                    <option value="">-- No Change --</option>
                                    {storageContainers
                                        .filter(container => {
                                            // If datacenter is selected, filter by datacenter
                                            if (bulkEditData.datacenter_id) {
                                                return container.datacenter_id === parseInt(bulkEditData.datacenter_id);
                                            }
                                            // If no datacenter selected, show all containers
                                            return true;
                                        })
                                        .map(container => {
                                            // Find room name if room_id exists
                                            const room = container.room_id ? rooms.find(r => r.id === container.room_id) : null;
                                            return (
                                                <option key={container.id} value={container.id}>
                                                    {container.name} ({container.container_type})
                                                    {room ? ` - ${room.name} ` : container.location ? ` - ${container.location} ` : ''}
                                                </option>
                                            );
                                        })}
                                </select>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {!bulkEditData.datacenter_id ? `Select a ${t('location').toLowerCase()} first` : ''}
                                </p>
                            </div>
                        </div>

                        {/* Cable/Transceiver Type-Specific Fields */}
                        {(bulkEditAssetTypeInfo.allAreDACCables ||
                            bulkEditAssetTypeInfo.allAreFiberCables ||
                            bulkEditAssetTypeInfo.allAreTransceivers ||
                            bulkEditAssetTypeInfo.allAreEthernetCables ||
                            bulkEditAssetTypeInfo.allAreCables) && (
                                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                    {/* DAC Cable Connector Types */}
                                    {bulkEditAssetTypeInfo.allAreDACCables && (
                                        <>
                                            <h3 className="text-lg font-semibold text-primary mb-3">🔌 DAC Cable Connector Types</h3>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                                                Set connector types for all selected DAC cables
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Connector End A
                                                    </label>
                                                    <select
                                                        value={bulkEditData.dac_connector_a}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, dac_connector_a: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <optgroup label="OSFP (800G)">
                                                            <option value="OSFP_FIN">OSFP Finned (Switch)</option>
                                                            <option value="OSFP_FLT">OSFP Flat (NIC/GPU)</option>
                                                            <option value="OSFP">OSFP (Generic)</option>
                                                        </optgroup>
                                                        <optgroup label="QSFP Family">
                                                            <option value="QSFP_DD">QSFP-DD (400G)</option>
                                                            <option value="QSFP112">QSFP112 (200/400G)</option>
                                                            <option value="QSFP56">QSFP56 (200G)</option>
                                                            <option value="QSFP28">QSFP28 (100G)</option>
                                                            <option value="QSFP_PLUS">QSFP+ (40G)</option>
                                                        </optgroup>
                                                        <optgroup label="SFP Family">
                                                            <option value="SFP28">SFP28 (25G)</option>
                                                            <option value="SFP_PLUS">SFP+ (10G)</option>
                                                            <option value="SFP">SFP (1G)</option>
                                                        </optgroup>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Connector End B
                                                    </label>
                                                    <select
                                                        value={bulkEditData.dac_connector_b}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, dac_connector_b: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <optgroup label="OSFP (800G)">
                                                            <option value="OSFP_FIN">OSFP Finned (Switch)</option>
                                                            <option value="OSFP_FLT">OSFP Flat (NIC/GPU)</option>
                                                            <option value="OSFP">OSFP (Generic)</option>
                                                        </optgroup>
                                                        <optgroup label="QSFP Family">
                                                            <option value="QSFP_DD">QSFP-DD (400G)</option>
                                                            <option value="QSFP112">QSFP112 (200/400G)</option>
                                                            <option value="QSFP56">QSFP56 (200G)</option>
                                                            <option value="QSFP28">QSFP28 (100G)</option>
                                                            <option value="QSFP_PLUS">QSFP+ (40G)</option>
                                                        </optgroup>
                                                        <optgroup label="SFP Family">
                                                            <option value="SFP28">SFP28 (25G)</option>
                                                            <option value="SFP_PLUS">SFP+ (10G)</option>
                                                            <option value="SFP">SFP (1G)</option>
                                                        </optgroup>
                                                    </select>
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {/* Fiber/AOC Cable Connector Types */}
                                    {bulkEditAssetTypeInfo.allAreFiberCables && (
                                        <>
                                            <h3 className="text-lg font-semibold text-primary mb-3">🌈 Fiber/AOC Cable Properties</h3>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                                                Set fiber properties for all selected cables
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Fiber Type
                                                    </label>
                                                    <select
                                                        value={bulkEditData.fiber_type}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, fiber_type: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <option value="SM">Single Mode (SM)</option>
                                                        <option value="MM">Multi Mode (MM)</option>
                                                        <option value="OM3">OM3 (Multi Mode)</option>
                                                        <option value="OM4">OM4 (Multi Mode)</option>
                                                        <option value="OM5">OM5 (Multi Mode)</option>
                                                        <option value="OS2">OS2 (Single Mode)</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Connector End A
                                                    </label>
                                                    <select
                                                        value={bulkEditData.fiber_connector_a}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, fiber_connector_a: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        {FIBER_CONNECTOR_OPTIONS.map(opt => (
                                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Connector End B
                                                    </label>
                                                    <select
                                                        value={bulkEditData.fiber_connector_b}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, fiber_connector_b: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        {FIBER_CONNECTOR_OPTIONS.map(opt => (
                                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {/* Transceiver Properties */}
                                    {bulkEditAssetTypeInfo.allAreTransceivers && (
                                        <>
                                            <h3 className="text-lg font-semibold text-primary mb-3">📡 Transceiver Properties</h3>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                                                Set transceiver properties for all selected modules
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Transceiver Type (Form Factor)
                                                    </label>
                                                    <select
                                                        value={bulkEditData.transceiver_type}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, transceiver_type: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <optgroup label="High Speed (400G+)">
                                                            <option value="OSFP">OSFP (800G/400G)</option>
                                                            <option value="QSFP_DD">QSFP-DD (400G)</option>
                                                        </optgroup>
                                                        <optgroup label="QSFP Family">
                                                            <option value="QSFP112">QSFP112 (200/400G)</option>
                                                            <option value="QSFP56">QSFP56 (200G)</option>
                                                            <option value="QSFP28">QSFP28 (100G)</option>
                                                            <option value="QSFP_PLUS">QSFP+ (40G)</option>
                                                        </optgroup>
                                                        <optgroup label="SFP Family">
                                                            <option value="SFP28">SFP28 (25G)</option>
                                                            <option value="SFP_PLUS">SFP+ (10G)</option>
                                                            <option value="SFP">SFP (1G)</option>
                                                        </optgroup>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Fiber Connector
                                                    </label>
                                                    <select
                                                        value={bulkEditData.fiber_connector}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, fiber_connector: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <option value="LC">LC (Duplex)</option>
                                                        <option value="MPO">MPO-12/16</option>
                                                        <option value="MTP">MTP-24</option>
                                                        <option value="SC">SC</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {/* Ethernet Cable Properties */}
                                    {bulkEditAssetTypeInfo.allAreEthernetCables && (
                                        <>
                                            <h3 className="text-lg font-semibold text-primary mb-3">🔗 Ethernet Cable Properties</h3>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                                                Set cable category for all selected ethernet cables
                                            </p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-primary mb-2">
                                                        Cable Category
                                                    </label>
                                                    <select
                                                        value={bulkEditData.ethernet_category}
                                                        onChange={(e) => setBulkEditData({ ...bulkEditData, ethernet_category: e.target.value })}
                                                        className="input w-full"
                                                    >
                                                        <option value="">-- No Change --</option>
                                                        <option value="Cat5e">Cat5e (1Gbps)</option>
                                                        <option value="Cat6">Cat6 (1Gbps/10Gbps)</option>
                                                        <option value="Cat6a">Cat6a (10Gbps)</option>
                                                        <option value="Cat7">Cat7 (10Gbps+)</option>
                                                        <option value="Cat8">Cat8 (25/40Gbps)</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                        {/* Port Template Application */}
                        {portTemplates.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                <h3 className="text-lg font-semibold text-primary mb-3">📋 Apply Port Template</h3>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                                    Apply a port template to all selected assets. This will create network ports based on the selected template.
                                </p>
                                <div className="grid grid-cols-1 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-primary mb-2">
                                            Select Template
                                        </label>
                                        <select
                                            value={selectedTemplateId || ''}
                                            onChange={(e) => setSelectedTemplateId(e.target.value ? parseInt(e.target.value) : null)}
                                            className="input w-full"
                                        >
                                            <option value="">-- Don't Apply Template --</option>
                                            {portTemplates.map(template => (
                                                <option key={template.id} value={template.id}>
                                                    {template.manufacturer} {template.model} ({template.port_definitions.length} ports)
                                                </option>
                                            ))}
                                        </select>
                                        {selectedTemplateId && (
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                {portTemplates.find(t => t.id === selectedTemplateId)?.description || ''}
                                            </p>
                                        )}
                                    </div>
                                    {selectedTemplateId && (
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                id="overwritePorts"
                                                checked={overwritePorts}
                                                onChange={(e) => setOverwritePorts(e.target.checked)}
                                                className="rounded"
                                            />
                                            <label htmlFor="overwritePorts" className="text-sm text-gray-600 dark:text-gray-300">
                                                Overwrite existing ports
                                            </label>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Form Actions */}
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                type="button"
                                onClick={closeBulkEditModal}
                                className="btn-secondary"
                                disabled={saving}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={saving}
                            >
                                {saving ? 'Updating...' : `Update ${selectedAssets.length} Assets`}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AssetBulkEditModal;
