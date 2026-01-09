// Asset Form Modal Component
// Extracted from Assets.tsx for better organization
// Handles both Add and Edit asset operations

import React from 'react';
import ImageUploadOCR from '../ImageUploadOCR';
import { Asset, AssetFormData, AssetType, Datacenter, Rack, Room, StorageContainer, PortTemplate } from '../../types/asset';
import { FIBER_CONNECTOR_OPTIONS, ASSET_STATUS_OPTIONS } from '../../constants/assetOptions';
import { getAvailablePositions } from '../RackView';
import { useCapabilities } from '../../contexts/CapabilityContext';

interface AssetFormModalProps {
  // Modal state
  showModal: boolean;
  editingAsset: Asset | null;

  // Form state
  formData: AssetFormData;
  setFormData: React.Dispatch<React.SetStateAction<AssetFormData>>;
  error: string | null;
  saving: boolean;

  // Image/OCR state
  uploadedImageUrl: string | null;
  setUploadedImageUrl: (url: string | null) => void;
  useManualSerial: boolean;
  setUseManualSerial: (value: boolean) => void;

  // Port template state
  portTemplates: PortTemplate[];
  selectedTemplateId: number | null;
  setSelectedTemplateId: (id: number | null) => void;
  overwritePorts: boolean;
  setOverwritePorts: (value: boolean) => void;

  // SKU autocomplete state
  skuLookupLoading: boolean;
  skuLookupError: string | null;
  skuAutocompleteSuggestions: Array<{ sku: string; usage_count: number }>;
  showSkuAutocomplete: boolean;
  setShowSkuAutocomplete: (show: boolean) => void;

  // Data lists
  assetTypes: AssetType[];
  datacenters: Datacenter[];
  racks: Rack[];
  rooms: Room[];
  storageContainers: StorageContainer[];
  assets: Asset[]; // For container_id dropdown

  // Handlers
  closeModal: () => void;
  handleSubmit: (e: React.FormEvent) => void;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void;
  handleOCRComplete: (ocrResult: any, imageUrl: string) => void;
  handleOCRClear: () => void;
  handleSKULookup: (sku: string) => void;
  fetchSkuAutocomplete: (query: string) => void;
  handleSkuAutocompleteSelect: (sku: string) => void;
  shouldShowField: (fieldName: string) => boolean;

  // Context
  t: (key: any) => string;
  verticalPack: string | null;
  hasFeature: (feature: any) => boolean;
}

const AssetFormModal: React.FC<AssetFormModalProps> = ({
  showModal,
  editingAsset,
  formData,
  setFormData,
  error,
  saving,
  uploadedImageUrl,
  setUploadedImageUrl,
  useManualSerial,
  setUseManualSerial,
  portTemplates,
  selectedTemplateId,
  setSelectedTemplateId,
  overwritePorts,
  setOverwritePorts,
  skuLookupLoading,
  skuLookupError,
  skuAutocompleteSuggestions,
  showSkuAutocomplete,
  setShowSkuAutocomplete,
  assetTypes,
  datacenters,
  racks,
  rooms,
  storageContainers,
  assets,
  closeModal,
  handleSubmit,
  handleInputChange,
  handleOCRComplete,
  handleOCRClear,
  handleSKULookup,
  fetchSkuAutocomplete,
  handleSkuAutocompleteSelect,
  shouldShowField,
  t,
  verticalPack,
  hasFeature,
}) => {
  const { capabilities } = useCapabilities();
  const isPremium = capabilities?.build_mode === 'premium';


  // Helper functions
  const selectedRack = formData.rack_id
    ? racks.find(r => r.id.toString() === formData.rack_id)
    : null;

  const availableRackPositions = React.useMemo(() =>
    formData.rack_id && selectedRack
      ? getAvailablePositions(
        parseInt(formData.rack_id, 10),
        parseInt(formData.height_u, 10) || 1,
        42, // Default rack size in U
        assets,
        editingAsset?.id
      )
      : [],
    [formData.rack_id, formData.height_u, assets, editingAsset?.id, selectedRack]
  );

  const isCableType = ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable'].includes(
    formData.asset_type?.toLowerCase() || ''
  );

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-primary">
              {editingAsset ? `Edit ${t('item')}` : `Add New ${t('item')}`}
            </h2>
            <button
              onClick={closeModal}
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

          {/* Image Upload & OCR Section */}
          {!editingAsset && (
            <div className="mb-6 p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg bg-subtle">
              <h3 className="text-lg font-semibold text-primary mb-3">
                {isPremium ? `Scan ${t('item')} Label (Optional)` : `Attach ${t('item')} Photo (Optional)`}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                {isPremium
                  ? `Upload or capture an image of the ${t('item').toLowerCase()} label to automatically extract information`
                  : `Upload or capture an image of the ${t('item').toLowerCase()} for your records`
                }
              </p>
              <ImageUploadOCR
                onOCRComplete={handleOCRComplete}
                onImageSelect={setUploadedImageUrl}
                onClear={handleOCRClear}
              />
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Asset Tag */}
              {shouldShowField('asset_tag') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Asset Tag <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="asset_tag"
                    value={formData.asset_tag}
                    onChange={handleInputChange}
                    required
                    className="input w-full"
                    placeholder="SRV-001"
                  />
                </div>
              )}

              {/* Serial Number */}
              {shouldShowField('serial_number') && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-primary">
                      Serial Number <span className="text-red-500">*</span>
                    </label>
                    {/* Toggle for cables: auto-generate vs manual entry */}
                    {(isCableType && !editingAsset) && (
                      <label className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={useManualSerial}
                          onChange={(e) => {
                            setUseManualSerial(e.target.checked);
                            // Clear serial number when switching modes
                            if (!e.target.checked) {
                              setFormData({ ...formData, serial_number: '', asset_tag: '' });
                            }
                          }}
                          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                        />
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {useManualSerial ? 'Manual Entry' : 'Auto-Generate'}
                        </span>
                      </label>
                    )}
                  </div>
                  <input
                    type="text"
                    name="serial_number"
                    value={formData.serial_number}
                    onChange={handleInputChange}
                    required
                    className="input w-full"
                    placeholder={
                      useManualSerial || !isCableType
                        ? "Enter serial number (or scan if available)"
                        : "Will be auto-generated"
                    }
                    disabled={!useManualSerial && isCableType && !editingAsset}
                  />
                  {!useManualSerial && isCableType && !editingAsset && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      A unique serial number with tenant code and check digit will be generated automatically
                    </p>
                  )}
                </div>
              )}

              {/* Asset Type */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Asset Type <span className="text-red-500">*</span>
                </label>
                <select
                  name="asset_type"
                  value={formData.asset_type}
                  onChange={handleInputChange}
                  required
                  className="input w-full"
                >
                  <option value="">Select type...</option>
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
                  Status <span className="text-red-500">*</span>
                </label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                  required
                  className="input w-full"
                >
                  {ASSET_STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* On Loan Checkbox */}
              {shouldShowField('on_loan') && (
                <div className="col-span-2">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      name="on_loan"
                      checked={formData.on_loan}
                      onChange={(e) => setFormData({ ...formData, on_loan: e.target.checked })}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-primary">On Loan</span>
                  </label>
                </div>
              )}

              {/* Loan Fields - Only show if on_loan is checked */}
              {formData.on_loan && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Loan Direction
                    </label>
                    <select
                      name="loan_direction"
                      value={formData.loan_direction}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="to_us">To Us (Borrowed)</option>
                      <option value="from_us">From Us (Loaned Out)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      {formData.loan_direction === 'from_us' ? 'Loaned To' : 'Borrowed From'}
                    </label>
                    <input
                      type="text"
                      name="loan_party"
                      value={formData.loan_party}
                      onChange={handleInputChange}
                      className="input w-full"
                      placeholder="Company or person name"
                    />
                  </div>

                  {formData.loan_direction === 'to_us' && (
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-primary mb-2">
                        Loan Source
                      </label>
                      <input
                        type="text"
                        name="loan_source"
                        value={formData.loan_source}
                        onChange={handleInputChange}
                        className="input w-full"
                        placeholder="Source or reference"
                      />
                    </div>
                  )}
                </>
              )}

              {/* Hostname */}
              {shouldShowField('hostname') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Hostname
                  </label>
                  <input
                    type="text"
                    name="hostname"
                    value={formData.hostname}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="server-01.example.com"
                  />
                </div>
              )}

              {/* Manufacturer */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Manufacturer <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="manufacturer"
                  value={formData.manufacturer}
                  onChange={handleInputChange}
                  required
                  className="input w-full"
                  placeholder="Dell, HP, Cisco, etc."
                />
              </div>

              {/* Model */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Model <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="model"
                  value={formData.model}
                  onChange={handleInputChange}
                  required
                  className="input w-full"
                  placeholder="PowerEdge R740"
                />
              </div>

              {/* SKU Field with autocomplete */}
              {hasFeature('sku_matching') && (
                <div className="col-span-2 relative">
                  <label className="block text-sm font-medium text-primary mb-2">
                    SKU (Optional)
                  </label>
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        name="sku"
                        value={formData.sku}
                        onChange={(e) => {
                          handleInputChange(e);
                          if (e.target.value.length >= 2) {
                            fetchSkuAutocomplete(e.target.value);
                          } else {
                            setShowSkuAutocomplete(false);
                          }
                        }}
                        onFocus={() => {
                          if (formData.sku.length >= 2 && skuAutocompleteSuggestions.length > 0) {
                            setShowSkuAutocomplete(true);
                          }
                        }}
                        className="input w-full"
                        placeholder="Enter FS.com SKU"
                      />

                      {/* Autocomplete Dropdown */}
                      {showSkuAutocomplete && skuAutocompleteSuggestions.length > 0 && (
                        <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-y-auto">
                          {skuAutocompleteSuggestions.map((suggestion, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => handleSkuAutocompleteSelect(suggestion.sku)}
                              className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between"
                            >
                              <span className="text-primary">{suggestion.sku}</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                Used {suggestion.usage_count}x
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSKULookup(formData.sku)}
                      disabled={!formData.sku || skuLookupLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      {skuLookupLoading ? 'Looking up...' : 'Lookup'}
                    </button>
                  </div>
                  {skuLookupError && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">{skuLookupError}</p>
                  )}
                </div>
              )}

              {/* Height (U) */}
              {shouldShowField('height_u') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Height (U)
                  </label>
                  <input
                    type="number"
                    name="height_u"
                    value={formData.height_u}
                    onChange={handleInputChange}
                    className="input w-full"
                    min="1"
                    placeholder="1"
                  />
                </div>
              )}

              {/* Power Consumption */}
              {shouldShowField('power_consumption_watts') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Power (Watts)
                  </label>
                  <input
                    type="number"
                    name="power_consumption_watts"
                    value={formData.power_consumption_watts}
                    onChange={handleInputChange}
                    className="input w-full"
                    min="0"
                    placeholder="350"
                  />
                </div>
              )}

              {/* Datacenter */}
              {shouldShowField('datacenter_id') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Datacenter
                  </label>
                  <select
                    name="datacenter_id"
                    value={formData.datacenter_id}
                    onChange={handleInputChange}
                    className="input w-full"
                  >
                    <option value="">Select datacenter...</option>
                    {datacenters.map(dc => (
                      <option key={dc.id} value={dc.id.toString()}>
                        {dc.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Rack */}
              {shouldShowField('rack_id') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Rack
                  </label>
                  <select
                    name="rack_id"
                    value={formData.rack_id}
                    onChange={handleInputChange}
                    className="input w-full"
                    disabled={!formData.datacenter_id}
                  >
                    <option value="">Select rack...</option>
                    {racks
                      .filter(r => r.datacenter_id.toString() === formData.datacenter_id)
                      .map(rack => (
                        <option key={rack.id} value={rack.id.toString()}>
                          {rack.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Rack Position */}
              {shouldShowField('rack_position_start') && formData.rack_id && (
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-primary mb-2">
                    Rack Position (Starting U)
                  </label>
                  {availableRackPositions.length > 0 ? (
                    <select
                      name="rack_position_start"
                      value={formData.rack_position_start}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select position...</option>
                      {availableRackPositions.map(pos => (
                        <option key={pos} value={pos.toString()}>
                          U{pos}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      name="rack_position_start"
                      value={formData.rack_position_start}
                      onChange={handleInputChange}
                      className="input w-full"
                      min="1"
                      placeholder="Bottom U position"
                    />
                  )}
                </div>
              )}

              {/* Storage Container */}
              {shouldShowField('storage_container_id') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Storage Container
                  </label>
                  <select
                    name="storage_container_id"
                    value={formData.storage_container_id}
                    onChange={handleInputChange}
                    className="input w-full"
                  >
                    <option value="">Select container...</option>
                    {storageContainers.map(container => (
                      <option key={container.id} value={container.id.toString()}>
                        {container.name} ({container.container_type})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Storage Location */}
              {shouldShowField('storage_location') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Storage Location
                  </label>
                  <input
                    type="text"
                    name="storage_location"
                    value={formData.storage_location}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="Shelf A, Row 3"
                  />
                </div>
              )}

              {/* Container (Asset as Container) */}
              {shouldShowField('container_id') && (
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-primary mb-2">
                    Inside Container (Asset)
                  </label>
                  <select
                    name="container_id"
                    value={formData.container_id}
                    onChange={handleInputChange}
                    className="input w-full"
                  >
                    <option value="">Not in a container...</option>
                    {assets
                      .filter(a => ['storage_box', 'storage_bin'].includes(a.asset_type?.toLowerCase()))
                      .map(container => (
                        <option key={container.id} value={container.id.toString()}>
                          {container.asset_tag} - {container.manufacturer} {container.model}
                        </option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Select a storage box or bin that contains this item
                  </p>
                </div>
              )}

              {/* Min Stock Threshold (for storage boxes/bins) */}
              {shouldShowField('min_stock_threshold') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Min Stock Threshold
                  </label>
                  <input
                    type="number"
                    name="min_stock_threshold"
                    value={formData.min_stock_threshold}
                    onChange={handleInputChange}
                    className="input w-full"
                    min="0"
                    placeholder="10"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Alert when stock falls below this level
                  </p>
                </div>
              )}

              {/* Cable Length */}
              {shouldShowField('cable_length') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Cable Length
                  </label>
                  <input
                    type="text"
                    name="cable_length"
                    value={formData.cable_length}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="3m, 10ft, etc."
                  />
                </div>
              )}

              {/* Quantity (for bulk items like cables) */}
              {shouldShowField('quantity') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Quantity
                  </label>
                  <input
                    type="number"
                    name="quantity"
                    value={formData.quantity}
                    onChange={handleInputChange}
                    className="input w-full"
                    min="1"
                    placeholder="1"
                  />
                </div>
              )}

              {/* Fiber-specific fields */}
              {formData.asset_type?.toLowerCase() === 'fiber_cable' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Fiber Type
                    </label>
                    <select
                      name="fiber_type"
                      value={formData.fiber_type}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select type...</option>
                      <option value="OM1">OM1 (62.5μm)</option>
                      <option value="OM2">OM2 (50μm)</option>
                      <option value="OM3">OM3 (50μm)</option>
                      <option value="OM4">OM4 (50μm)</option>
                      <option value="OM5">OM5 (50μm)</option>
                      <option value="OS1">OS1 (9μm SM)</option>
                      <option value="OS2">OS2 (9μm SM)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Connector End A
                    </label>
                    <select
                      name="fiber_connector_a"
                      value={formData.fiber_connector_a}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select connector...</option>
                      {FIBER_CONNECTOR_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Connector End B
                    </label>
                    <select
                      name="fiber_connector_b"
                      value={formData.fiber_connector_b}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select connector...</option>
                      {FIBER_CONNECTOR_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Breakout Configuration
                    </label>
                    <input
                      type="text"
                      name="fiber_breakout"
                      value={formData.fiber_breakout}
                      onChange={handleInputChange}
                      className="input w-full"
                      placeholder="e.g., 1x12, 2x6"
                    />
                  </div>
                </>
              )}

              {/* DAC-specific fields */}
              {formData.asset_type?.toLowerCase() === 'dac_cable' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Speed Rating
                    </label>
                    <select
                      name="dac_speed"
                      value={formData.dac_speed}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select speed...</option>
                      <option value="10G">10G</option>
                      <option value="25G">25G</option>
                      <option value="40G">40G</option>
                      <option value="100G">100G</option>
                      <option value="200G">200G</option>
                      <option value="400G">400G</option>
                      <option value="800G">800G</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Connector End A
                    </label>
                    <select
                      name="dac_connector_a"
                      value={formData.dac_connector_a}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select connector...</option>
                      <option value="SFP+">SFP+</option>
                      <option value="SFP28">SFP28</option>
                      <option value="SFP56">SFP56</option>
                      <option value="QSFP+">QSFP+</option>
                      <option value="QSFP28">QSFP28</option>
                      <option value="QSFP56">QSFP56</option>
                      <option value="QSFP-DD">QSFP-DD</option>
                      <option value="OSFP">OSFP</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Connector End B
                    </label>
                    <select
                      name="dac_connector_b"
                      value={formData.dac_connector_b}
                      onChange={handleInputChange}
                      className="input w-full"
                    >
                      <option value="">Select connector...</option>
                      <option value="SFP+">SFP+</option>
                      <option value="SFP28">SFP28</option>
                      <option value="SFP56">SFP56</option>
                      <option value="QSFP+">QSFP+</option>
                      <option value="QSFP28">QSFP28</option>
                      <option value="QSFP56">QSFP56</option>
                      <option value="QSFP-DD">QSFP-DD</option>
                      <option value="OSFP">OSFP</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Breakout Configuration
                    </label>
                    <input
                      type="text"
                      name="dac_breakout"
                      value={formData.dac_breakout}
                      onChange={handleInputChange}
                      className="input w-full"
                      placeholder="e.g., 1x4, 2x2"
                    />
                  </div>
                </>
              )}

              {/* Ethernet Cable Category */}
              {formData.asset_type?.toLowerCase() === 'ethernet_cable' && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Cable Category
                  </label>
                  <select
                    name="ethernet_category"
                    value={formData.ethernet_category}
                    onChange={handleInputChange}
                    className="input w-full"
                  >
                    <option value="">Select category...</option>
                    <option value="Cat5">Cat5</option>
                    <option value="Cat5e">Cat5e</option>
                    <option value="Cat6">Cat6</option>
                    <option value="Cat6a">Cat6a</option>
                    <option value="Cat7">Cat7</option>
                    <option value="Cat8">Cat8</option>
                  </select>
                </div>
              )}

              {/* Transceiver Connector Type */}
              {shouldShowField('connector_type') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Connector Type
                  </label>
                  <input
                    type="text"
                    name="connector_type"
                    value={formData.connector_type}
                    onChange={handleInputChange}
                    className="input w-full"
                    placeholder="LC, SC, RJ45, etc."
                  />
                </div>
              )}

              {/* Purchase Info */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Purchase Cost
                </label>
                <input
                  type="number"
                  name="purchase_cost"
                  value={formData.purchase_cost}
                  onChange={handleInputChange}
                  className="input w-full"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Currency
                </label>
                <select
                  name="currency"
                  value={formData.currency}
                  onChange={handleInputChange}
                  className="input w-full"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="CNY">CNY</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Purchase Date
                </label>
                <input
                  type="date"
                  name="purchase_date"
                  value={formData.purchase_date}
                  onChange={handleInputChange}
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Supplier
                </label>
                <input
                  type="text"
                  name="supplier"
                  value={formData.supplier}
                  onChange={handleInputChange}
                  className="input w-full"
                  placeholder="Dell, CDW, etc."
                />
              </div>

              <div className="col-span-2">
                <label className="block text-sm font-medium text-primary mb-2">
                  PO Number
                </label>
                <input
                  type="text"
                  name="po_number"
                  value={formData.po_number}
                  onChange={handleInputChange}
                  className="input w-full"
                  placeholder="Purchase order number"
                />
              </div>

              {/* Warranty Info */}
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Warranty Start
                </label>
                <input
                  type="date"
                  name="warranty_start_date"
                  value={formData.warranty_start_date}
                  onChange={handleInputChange}
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Warranty End
                </label>
                <input
                  type="date"
                  name="warranty_end_date"
                  value={formData.warranty_end_date}
                  onChange={handleInputChange}
                  className="input w-full"
                />
              </div>

              {/* Description */}
              <div className="col-span-2">
                <label className="block text-sm font-medium text-primary mb-2">
                  Description / Notes
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  className="input w-full"
                  rows={3}
                  placeholder="Additional notes or description..."
                />
              </div>

              {/* Port Template Selection (for switches) */}
              {editingAsset && portTemplates.length > 0 && (
                <div className="col-span-2 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <h4 className="text-sm font-semibold text-primary mb-3">
                    Port Template (Optional)
                  </h4>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                    Apply a pre-defined port configuration template to this asset
                  </p>

                  <div className="space-y-3">
                    <select
                      value={selectedTemplateId || ''}
                      onChange={(e) => setSelectedTemplateId(e.target.value ? parseInt(e.target.value) : null)}
                      className="input w-full"
                    >
                      <option value="">No template</option>
                      {portTemplates.map(template => (
                        <option key={template.id} value={template.id}>
                          {template.manufacturer} {template.model} ({template.port_definitions.length} ports)
                        </option>
                      ))}
                    </select>

                    {selectedTemplateId && (
                      <label className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={overwritePorts}
                          onChange={(e) => setOverwritePorts(e.target.checked)}
                          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          Overwrite existing ports
                        </span>
                      </label>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Form Actions */}
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
              <button
                type="button"
                onClick={closeModal}
                disabled={saving}
                className="px-6 py-2 border border-gray-300 dark:border-gray-600 text-primary rounded-lg hover:bg-subtle transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition disabled:opacity-50"
              >
                {saving ? 'Saving...' : editingAsset ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AssetFormModal;
