// Asset Table Component
// Extracted from Assets.tsx for better organization

import React from 'react';
import { Link } from 'react-router-dom';
import { Asset } from '../../types/asset';
import { formatStatus } from '../../utils/formatStatus';

interface AssetGroup {
  key: string;
  assets: Asset[];
  assetType: string;
  manufacturer: string;
  model: string;
  status: string;
}

interface AssetTableProps {
  // Data
  loading: boolean;
  filteredAssets: Asset[];
  groupedAssets: AssetGroup[];
  selectedAssets: number[];
  expandedGroups: Set<string>;
  assets: Asset[]; // For total count display
  isAuthenticated: boolean;

  // Sorting
  sortColumn: keyof Asset | null;
  sortDirection: 'asc' | 'desc';

  // Handlers
  handleSelectAll: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleSort: (column: keyof Asset) => void;
  handleSelectAsset: (assetId: number) => void;
  handleSelectGroup: (groupAssets: Asset[], isSelected: boolean) => void;
  openEditModal: (asset: Asset) => void;
  handleDelete: (assetId: number) => void;
  setPrintingAsset: (asset: Asset) => void;
  setShowLabelPrint: (show: boolean) => void;
  toggleGroup: (groupKey: string) => void;

  // Helper functions
  getSortIndicator: (column: keyof Asset) => string;
  shouldShowColumn: (columnName: string) => boolean;
  getStatusBadge: (status: string) => string;
  getLocationDisplay: (asset: Asset) => string;
  getAssetTypeDisplayName: (type: string) => string;
  getDatacenterName: (datacenterId?: number) => string;
  getAssetDatacenterId: (asset: Asset) => number | undefined;

  // Context/translations
  t: (key: any) => string;
}

const AssetTable: React.FC<AssetTableProps> = ({
  loading,
  filteredAssets,
  groupedAssets,
  selectedAssets,
  expandedGroups,
  assets,
  isAuthenticated,
  sortColumn,
  sortDirection,
  handleSelectAll,
  handleSort,
  handleSelectAsset,
  handleSelectGroup,
  openEditModal,
  handleDelete,
  setPrintingAsset,
  setShowLabelPrint,
  toggleGroup,
  getSortIndicator,
  shouldShowColumn,
  getStatusBadge,
  getLocationDisplay,
  getAssetTypeDisplayName,
  getDatacenterName,
  getAssetDatacenterId,
  t,
}) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500 dark:text-gray-400">Loading {t('items').toLowerCase()}...</div>
      </div>
    );
  }

  // Helper to determine location display for a group
  const getGroupLocationDisplay = (group: AssetGroup): string => {
    const { assets } = group;
    if (!assets || assets.length === 0) return 'various';

    // Check if all assets in the group share the same location string
    const firstDisplay = getLocationDisplay(assets[0]);
    const allSame = assets.every(a => getLocationDisplay(a) === firstDisplay);

    return allSame ? firstDisplay : 'various';
  };

  return (
    <div className="card overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th className="w-12">
              <input
                type="checkbox"
                onChange={handleSelectAll}
                checked={filteredAssets.length > 0 && selectedAssets.length === filteredAssets.length}
                className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
            </th>
            {shouldShowColumn('hostname') && (
              <th
                className="cursor-pointer hover:bg-table-row-hover select-none text-primary"
                onClick={() => handleSort('hostname')}
              >
                Hostname{getSortIndicator('hostname')}
              </th>
            )}
            <th
              className="cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none text-primary"
              onClick={() => handleSort('asset_type')}
            >
              {t('category')}{getSortIndicator('asset_type')}
            </th>
            <th
              className="cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none text-primary"
              onClick={() => handleSort('manufacturer')}
            >
              Manufacturer{getSortIndicator('manufacturer')}
            </th>
            <th
              className="cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none text-primary"
              onClick={() => handleSort('model')}
            >
              Model{getSortIndicator('model')}
            </th>
            <th
              className="cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 select-none text-primary"
              onClick={() => handleSort('status')}
            >
              {t('lifecycle')}{getSortIndicator('status')}
            </th>
            {shouldShowColumn('quantity') && (
              <th className="text-primary">Quantity</th>
            )}
            {shouldShowColumn('asset_tag') && (
              <th
                className="cursor-pointer hover:bg-table-row-hover select-none text-primary text-xs px-2"
                onClick={() => handleSort('asset_tag')}
              >
                {t('item')} Tag{getSortIndicator('asset_tag')}
              </th>
            )}
            {shouldShowColumn('serial_number') && (
              <th
                className="cursor-pointer hover:bg-table-row-hover select-none text-primary hide-lg text-xs px-2"
                onClick={() => handleSort('serial_number')}
              >
                Serial{getSortIndicator('serial_number')}
              </th>
            )}
            <th className="text-primary text-xs px-2">{t('location')}</th>
            <th className="text-primary">Actions</th>
          </tr>
        </thead>
        <tbody>
          {filteredAssets.length === 0 ? (
            <tr>
              <td colSpan={
                1 + // checkbox
                (shouldShowColumn('hostname') ? 1 : 0) +
                4 + // type, manufacturer, model, status
                (shouldShowColumn('quantity') ? 1 : 0) +
                (shouldShowColumn('asset_tag') ? 1 : 0) +
                (shouldShowColumn('serial_number') ? 1 : 0) +
                1 + // location
                1 // actions
              } className="text-center py-8 text-gray-500 dark:text-gray-400">
                No {t('items').toLowerCase()} found
              </td>
            </tr>
          ) : (
            groupedAssets.map((group) => {
              const isExpanded = expandedGroups.has(group.key);
              const isSingleItem = group.assets.length === 1;
              const allGroupSelected = group.assets.every(a => selectedAssets.includes(a.id));
              const someGroupSelected = group.assets.some(a => selectedAssets.includes(a.id));

              // For single-item groups, render normally (no grouping)
              if (isSingleItem) {
                const asset = group.assets[0];
                return (
                  <tr key={asset.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedAssets.includes(asset.id)}
                        onChange={() => handleSelectAsset(asset.id)}
                        className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                    </td>
                    {shouldShowColumn('hostname') && (
                      <td className="text-primary">
                        {asset.hostname ? (
                          <Link
                            to={`/assets/${asset.id}`}
                            className="text-primary hover:text-primary-hover dark:text-accent dark:hover:text-accent/80 hover:underline"
                          >
                            {asset.hostname}
                          </Link>
                        ) : '-'}
                      </td>
                    )}
                    <td className="text-primary">{getAssetTypeDisplayName(asset.asset_type)}</td>
                    <td className="text-primary max-w-[120px] overflow-hidden text-ellipsis whitespace-nowrap" title={asset.manufacturer}>{asset.manufacturer}</td>
                    <td className="text-primary max-w-[120px] overflow-hidden text-ellipsis whitespace-nowrap" title={asset.model}>{asset.model}</td>
                    <td>
                      <span className={getStatusBadge(asset.status)}>
                        {formatStatus(asset.status)}
                      </span>
                      {asset.on_loan && (
                        <span
                          className="badge badge-info ml-2"
                          title={
                            asset.loan_direction === 'from_us'
                              ? (asset.loan_party ? `Loaned to: ${asset.loan_party}` : 'Loaned out')
                              : (asset.loan_party || asset.loan_source ? `On loan from: ${asset.loan_party || asset.loan_source}` : 'On loan')
                          }
                        >
                          {asset.loan_direction === 'from_us' ? '📤 Loaned Out' : '📋 On Loan'}
                        </span>
                      )}
                    </td>
                    {shouldShowColumn('quantity') && (
                      <td className="font-semibold text-primary">
                        {asset.custom_fields?.quantity || '-'}
                      </td>
                    )}
                    {shouldShowColumn('asset_tag') && (
                      <td className="font-medium text-primary text-xs px-2">{asset.asset_tag}</td>
                    )}
                    {shouldShowColumn('serial_number') && (
                      <td className="text-primary hide-lg text-xs px-2">{asset.serial_number}</td>
                    )}
                    <td className="text-primary text-xs px-2">
                      {getLocationDisplay(asset)}
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          onClick={() => {
                            setPrintingAsset(asset);
                            setShowLabelPrint(true);
                          }}
                          className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300"
                          title="Print label"
                        >
                          🏷️
                        </button>
                        {isAuthenticated && (
                          <>
                            <button
                              onClick={() => openEditModal(asset)}
                              className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(asset.id)}
                              className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                            >
                              Del
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              }

              // For multi-item groups, render summary row with expand/collapse
              return (
                <React.Fragment key={group.key}>
                  {/* Group Summary Row */}
                  <tr
                    className="bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
                    onClick={() => toggleGroup(group.key)}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={allGroupSelected}
                        ref={(el) => { if (el) el.indeterminate = someGroupSelected && !allGroupSelected; }}
                        onChange={(e) => handleSelectGroup(group.assets, e.target.checked)}
                        className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                    </td>
                    {shouldShowColumn('hostname') && (
                      <td className="text-primary font-medium">
                        <span className="mr-2">{isExpanded ? '▼' : '▶'}</span>
                        <span className="text-gray-500">({group.assets.length} items)</span>
                      </td>
                    )}
                    {!shouldShowColumn('hostname') && (
                      <td className="text-primary font-medium">
                        <span className="mr-2">{isExpanded ? '▼' : '▶'}</span>
                        {getAssetTypeDisplayName(group.assetType)}
                        <span className="ml-2 text-blue-600 dark:text-blue-400 font-bold">×{group.assets.length}</span>
                      </td>
                    )}
                    {shouldShowColumn('hostname') && (
                      <td className="text-primary font-medium">
                        {getAssetTypeDisplayName(group.assetType)}
                        <span className="ml-2 text-blue-600 dark:text-blue-400 font-bold">×{group.assets.length}</span>
                      </td>
                    )}
                    <td className="text-primary">{group.manufacturer}</td>
                    <td className="text-primary">{group.model}</td>
                    <td>
                      <span className={getStatusBadge(group.status)}>
                        {formatStatus(group.status)}
                      </span>
                    </td>
                    {shouldShowColumn('quantity') && (
                      <td className="text-primary">-</td>
                    )}
                    {shouldShowColumn('asset_tag') && (
                      <td className="text-gray-400 italic">multiple</td>
                    )}
                    {shouldShowColumn('serial_number') && (
                      <td className="text-gray-400 italic hide-lg">multiple</td>
                    )}
                    <td className="text-gray-400 italic">{getGroupLocationDisplay(group)}</td>
                    <td>
                      <span className="text-gray-500 text-sm">Click to {isExpanded ? 'collapse' : 'expand'}</span>
                    </td>
                  </tr>

                  {/* Expanded Items */}
                  {isExpanded && group.assets.map((asset) => (
                    <tr key={asset.id} className="bg-blue-50/30 dark:bg-blue-900/10">
                      <td className="pl-6">
                        <input
                          type="checkbox"
                          checked={selectedAssets.includes(asset.id)}
                          onChange={() => handleSelectAsset(asset.id)}
                          className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                        />
                      </td>
                      {shouldShowColumn('hostname') && (
                        <td className="text-primary pl-6">
                          {asset.hostname ? (
                            <Link
                              to={`/assets/${asset.id}`}
                              className="text-primary hover:text-primary-hover dark:text-accent dark:hover:text-accent/80 hover:underline"
                            >
                              {asset.hostname}
                            </Link>
                          ) : '-'}
                        </td>
                      )}
                      <td className="text-primary text-gray-400">↳</td>
                      <td className="text-primary">{asset.manufacturer}</td>
                      <td className="text-primary">{asset.model}</td>
                      <td>
                        <span className={getStatusBadge(asset.status)}>
                          {formatStatus(asset.status)}
                        </span>
                      </td>
                      {shouldShowColumn('quantity') && (
                        <td className="font-semibold text-primary">
                          {asset.custom_fields?.quantity || '-'}
                        </td>
                      )}
                      {shouldShowColumn('asset_tag') && (
                        <td className="font-medium text-primary">{asset.asset_tag}</td>
                      )}
                      {shouldShowColumn('serial_number') && (
                        <td className="text-primary hide-lg">{asset.serial_number}</td>
                      )}
                      <td className="text-primary">
                        {getLocationDisplay(asset)}
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            onClick={() => {
                              setPrintingAsset(asset);
                              setShowLabelPrint(true);
                            }}
                            className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300"
                            title="Print label"
                          >
                            🏷️
                          </button>
                          {isAuthenticated && (
                            <>
                              <button
                                onClick={() => openEditModal(asset)}
                                className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(asset.id)}
                                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                              >
                                Del
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              );
            })
          )}
        </tbody>
      </table>

      {filteredAssets.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Showing {filteredAssets.length} of {assets.length} {t('items').toLowerCase()}
          </p>
        </div>
      )}
    </div>
  );
};

export default AssetTable;
