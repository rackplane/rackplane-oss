// Asset Filters Component
// Extracted from Assets.tsx for reusability

import React from 'react';
import { AssetType } from '../../types/asset';
import { formatAssetType } from '../../utils/formatAssetType';
import { formatStatus } from '../../utils/formatStatus';
import { MAX_QUICK_FILTER_BUTTONS, ASSET_STATUS_OPTIONS } from '../../constants/assetOptions';

interface QuickFilterItem {
    type: string;
    count: number;
}

interface AssetFiltersProps {
    // Search
    search: string;
    onSearchChange: (value: string) => void;

    // Type filter
    typeFilter: string;
    onTypeFilterChange: (value: string) => void;
    assetTypes: AssetType[];
    topAssetTypeFilters: QuickFilterItem[];

    // Status filter
    statusFilter: string;
    onStatusFilterChange: (value: string) => void;

    // Hide storage boxes toggle
    hideStorageBoxes: boolean;
    onHideStorageBoxesChange: (value: boolean) => void;

    // Total count for display
    totalCount: number;

    // Translation function (from useWhiteLabel)
    t: (key: any) => string;

    // Helper function to get display name
    getAssetTypeDisplayName: (type: string) => string;
}

const AssetFilters: React.FC<AssetFiltersProps> = ({
    search,
    onSearchChange,
    typeFilter,
    onTypeFilterChange,
    assetTypes,
    topAssetTypeFilters,
    statusFilter,
    onStatusFilterChange,
    hideStorageBoxes,
    onHideStorageBoxesChange,
    totalCount,
    t,
    getAssetTypeDisplayName,
}) => {
    const hasActiveFilters = search || typeFilter || statusFilter;

    const clearAllFilters = () => {
        onSearchChange('');
        onTypeFilterChange('');
        onStatusFilterChange('');
    };

    return (
        <div className="bg-card rounded-lg p-4 mb-6">
            {/* Search Input */}
            <div className="mb-4">
                <label className="block text-sm font-medium text-primary mb-2">Search {t('items')}:</label>
                <input
                    type="text"
                    placeholder={`Search by asset tag, serial number, manufacturer, model...`}
                    className="input w-full"
                    value={search}
                    onChange={(e) => onSearchChange(e.target.value)}
                />
            </div>

            {/* Hide Storage Boxes Toggle */}
            <div className="mb-4">
                <label className="flex items-center gap-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={hideStorageBoxes}
                        onChange={(e) => onHideStorageBoxesChange(e.target.checked)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-primary">Hide {t('container').toLowerCase()}s from {t('stock').toLowerCase()}</span>
                </label>
            </div>

            {/* Quick Filter Buttons */}
            <div className="mb-4">
                <label className="block text-sm font-medium text-primary mb-2">Quick Filters:</label>
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => onTypeFilterChange('')}
                        className={`px-4 py-2 rounded-lg font-medium transition ${typeFilter === ''
                            ? 'bg-primary text-white'
                            : 'bg-button-secondary hover:bg-button-secondary'
                            }`}
                    >
                        All {t('items')} ({totalCount})
                    </button>
                    {topAssetTypeFilters.slice(0, MAX_QUICK_FILTER_BUTTONS).map(({ type, count }) => (
                        <button
                            key={type}
                            onClick={() => onTypeFilterChange(type.toLowerCase())}
                            className={`px-4 py-2 rounded-lg font-medium transition ${typeFilter === type.toLowerCase()
                                ? 'bg-primary text-white'
                                : 'bg-button-secondary hover:bg-button-secondary'
                                }`}
                        >
                            {formatAssetType(type)} ({count})
                        </button>
                    ))}
                </div>
            </div>

            {/* Advanced Filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-primary mb-2">Filter by Type:</label>
                    <select
                        className="input w-full"
                        value={typeFilter}
                        onChange={(e) => onTypeFilterChange(e.target.value)}
                    >
                        <option value="">All Types</option>
                        {assetTypes.map(type => (
                            <option key={type.id} value={type.name}>
                                {type.display_name}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-primary mb-2">Filter by Status:</label>
                    <select
                        className="input w-full"
                        value={statusFilter}
                        onChange={(e) => onStatusFilterChange(e.target.value)}
                    >
                        <option value="">All Status</option>
                        {ASSET_STATUS_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Active Filters Display */}
            {hasActiveFilters && (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-primary">Active Filters:</span>
                    {search && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
                            Search: "{search}"
                            <button
                                onClick={() => onSearchChange('')}
                                className="ml-2 hover:text-blue-900"
                            >
                                ×
                            </button>
                        </span>
                    )}
                    {typeFilter && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
                            Type: {getAssetTypeDisplayName(typeFilter)}
                            <button
                                onClick={() => onTypeFilterChange('')}
                                className="ml-2 hover:text-green-900"
                            >
                                ×
                            </button>
                        </span>
                    )}
                    {statusFilter && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-800">
                            Status: {formatStatus(statusFilter)}
                            <button
                                onClick={() => onStatusFilterChange('')}
                                className="ml-2 hover:text-purple-900"
                            >
                                ×
                            </button>
                        </span>
                    )}
                    <button
                        onClick={clearAllFilters}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                    >
                        Clear All
                    </button>
                </div>
            )}
        </div>
    );
};

export default AssetFilters;
