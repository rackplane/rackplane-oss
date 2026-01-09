// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState } from 'react';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number?: string;  // Optional to match usage in RackDetail
  manufacturer?: string;
  model?: string;
  hostname?: string;
  rack_id?: number;
  rack_position_start?: number;  // Starting U position (bottom)
  rack_position_end?: number;      // Ending U position (top)
  height_u?: number;              // Height in rack units
  status?: string;
  asset_type?: string;
}

interface RackViewProps {
  rackId: number;
  rackName: string;
  rackCode: string;
  rackSize?: number;  // Default 42U
  assets: Asset[];
  onAssetClick?: (asset: Asset) => void;
  onUnitClick?: (unit: number) => void;
  showAssetListOnHover?: boolean;  // Default true, set to false to disable hover list
}

export const RackView: React.FC<RackViewProps> = ({
  rackId,
  rackName,
  rackCode,
  rackSize = 42,
  assets,
  onAssetClick,
  onUnitClick,
  showAssetListOnHover = true
}) => {
  const [showAssetList, setShowAssetList] = useState(false);

  // Filter assets for this rack - only show assets that are actually mounted (have rack_position_start)
  // CRITICAL: Must match rackId exactly - convert both to numbers for comparison
  const rackAssets = assets.filter(asset => {
    // Normalize rack IDs to numbers for comparison
    const assetRackId = typeof asset.rack_id === 'number'
      ? asset.rack_id
      : (asset.rack_id ? parseInt(String(asset.rack_id), 10) : 0);
    const propRackId = typeof rackId === 'number'
      ? rackId
      : parseInt(String(rackId), 10);

    // Must match rack ID AND have a valid position
    const hasPosition = asset.rack_position_start && asset.rack_position_start >= 1;
    const matches = assetRackId === propRackId && hasPosition;

    return matches;
  });

  // Create an array of units, reversed so U42 is at top, U1 is at bottom
  const units = Array.from({ length: rackSize }, (_, i) => rackSize - i);

  // Helper to get the device at a specific unit
  const getDeviceAtUnit = (u: number): Asset | null => {
    return rackAssets.find(asset => {
      // Ensure rack_position_start is a number
      const start = typeof asset.rack_position_start === 'number'
        ? asset.rack_position_start
        : parseInt(String(asset.rack_position_start || '0'), 10);

      // Skip assets without valid positions
      if (!start || start < 1) {
        return false;
      }

      // Calculate end position: use rack_position_end if set, otherwise calculate from height_u
      let end: number;
      const rackEnd = typeof asset.rack_position_end === 'number'
        ? asset.rack_position_end
        : (asset.rack_position_end ? parseInt(String(asset.rack_position_end), 10) : null);
      const heightU = typeof asset.height_u === 'number'
        ? asset.height_u
        : (asset.height_u ? parseInt(String(asset.height_u), 10) : null);

      if (rackEnd && rackEnd >= start) {
        end = rackEnd;
      } else if (heightU && heightU > 0) {
        end = start + heightU - 1;
      } else {
        // Default to 1U if no height specified
        end = start;
      }

      // Check if unit u is within the range [start, end] (inclusive)
      return u >= start && u <= end;
    }) || null;
  };

  // Helper to check if a unit is the start of a device
  const isDeviceStart = (u: number, device: Asset | null): boolean => {
    if (!device) return false;
    const deviceStart = typeof device.rack_position_start === 'number'
      ? device.rack_position_start
      : parseInt(String(device.rack_position_start || '0'), 10);
    return deviceStart === u;
  };

  // Helper to get device display name (without asset tag)
  const getDeviceDisplayName = (device: Asset): string => {
    // Prefer manufacturer + model, then model, then asset type
    if (device.manufacturer && device.model) {
      return `${device.manufacturer} ${device.model}`;
    }
    if (device.model) return device.model;
    if (device.asset_type) return device.asset_type;
    return `Device ${device.id}`;
  };

  // Helper to get device height for display
  const getDeviceHeight = (device: Asset): number => {
    if (device.rack_position_start && device.rack_position_end && device.rack_position_end >= device.rack_position_start) {
      return device.rack_position_end - device.rack_position_start + 1;
    }
    // Fall back to height_u if available, otherwise default to 1U
    return device.height_u && device.height_u > 0 ? device.height_u : 1;
  };

  // Calculate occupied units for collision detection
  const getOccupiedUnits = (): Set<number> => {
    const occupied = new Set<number>();
    rackAssets.forEach(asset => {
      // Only count assets with valid rack positions
      if (!asset.rack_position_start || asset.rack_position_start < 1) {
        return; // Skip assets without valid positions
      }

      const start = asset.rack_position_start;
      // Calculate end position: use rack_position_end if set, otherwise calculate from height_u
      let end: number;
      if (asset.rack_position_end && asset.rack_position_end >= start) {
        end = asset.rack_position_end;
      } else if (asset.height_u && asset.height_u > 0) {
        end = start + asset.height_u - 1;
      } else {
        // Default to 1U if no height specified
        end = start;
      }

      // Only add valid U positions (1 to rackSize)
      for (let u = start; u <= end && u <= rackSize; u++) {
        if (u >= 1) {
          occupied.add(u);
        }
      }
    });
    return occupied;
  };

  const occupiedUnits = getOccupiedUnits();

  return (
    <div
      className="relative bg-card rounded-lg shadow-lg p-3"
      onMouseEnter={showAssetListOnHover ? () => setShowAssetList(true) : undefined}
      onMouseLeave={showAssetListOnHover ? () => setShowAssetList(false) : undefined}
    >
      <div className="flex gap-4">
        {/* Left side: Rack info and visualization */}
        <div className="flex-1">
          <div className="mb-4">
            <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">{rackCode}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">{rackName}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {rackAssets.length} device(s) installed • {occupiedUnits.size}/{rackSize}U used
            </p>
          </div>

          {/* Rack Visualization */}
          <div className="w-80 mx-auto">
            <div className="border-4 border-default bg-subtle-card rounded-lg shadow-xl" style={{ paddingTop: '8px', paddingLeft: '8px', paddingRight: '8px', paddingBottom: '0px', marginBottom: '0px' }}>
              <div className="flex">
                {/* Left side: Unit labels (ruler) */}
                <div className="flex flex-col pr-1 border-r border-gray-300 dark:border-gray-600" style={{ gap: '2px' }}>
                  {units.map((u) => {
                    const device = getDeviceAtUnit(u);
                    const isStart = isDeviceStart(u, device);

                    // For multi-U devices, don't render labels for inside units (only render at start)
                    if (device && !isStart) {
                      return null;
                    }

                    // For devices, show label aligned to top
                    // Height is just units * 36px - flex gap handles spacing between elements
                    if (device && isStart) {
                      const height = getDeviceHeight(device);
                      const heightPx = height * 36; // 36px per U, gap is handled by flex container
                      return (
                        <div
                          key={u}
                          className="flex items-start justify-end text-[10px] font-mono text-gray-500 dark:text-gray-400 pr-1 pt-0.5"
                          style={{ height: `${heightPx}px` }}
                        >
                          U{u}
                        </div>
                      );
                    }

                    // Empty slot
                    return (
                      <div
                        key={u}
                        className="h-[36px] flex items-center justify-end text-[10px] font-mono text-gray-500 dark:text-gray-400 pr-1"
                      >
                        U{u}
                      </div>
                    );
                  })}
                </div>

                {/* Right side: Rack units */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden" style={{ gap: '2px', marginBottom: '0px', paddingBottom: '0px', minHeight: 'fit-content' }}>
                  {units.map((u) => {
                    const device = getDeviceAtUnit(u);
                    const isStart = isDeviceStart(u, device);

                    // If this unit is the START of a device, render the device block
                    if (device && isStart) {
                      const height = getDeviceHeight(device);
                      // Height is just units * 36px - flex gap handles spacing between elements
                      const heightPx = height * 36; // 36px per U, gap is handled by flex container

                      return (
                        <div
                          key={u}
                          onClick={(e) => {
                            e.stopPropagation(); // Prevent event from bubbling to parent elements
                            if (onAssetClick) {
                              onAssetClick(device);
                            }
                          }}
                          style={{ height: `${heightPx}px` }}
                          className={`
                          bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono 
                          flex items-center justify-center border border-blue-800 rounded 
                          cursor-pointer transition-colors shadow-sm overflow-hidden min-w-0
                          ${device.status === 'maintenance' ? 'bg-yellow-600 hover:bg-yellow-500' : ''}
                          ${device.status === 'failed' ? 'bg-red-600 hover:bg-red-500' : ''}
                        `}
                          title={`${device.asset_tag || 'No Tag'} - ${getDeviceDisplayName(device)} (${height}U) - ${device.status || 'active'}`}
                        >
                          <div className="text-center px-1 w-full min-w-0 overflow-hidden">
                            <div className="font-semibold truncate">{getDeviceDisplayName(device)}</div>
                            {device.hostname && (
                              <div className="text-[9px] opacity-90 mt-0.5 truncate font-mono" title={device.hostname}>
                                {device.hostname.length > 20 ? device.hostname.substring(0, 17) + '...' : device.hostname}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    }

                    // If this unit is "inside" a multi-U device, return null
                    // The device block above already covers this visually
                    // The flex gap will handle spacing, and device blocks are sized to account for gaps
                    if (device && !isStart) {
                      return null;
                    }

                    // Empty Slot - with visual polish (rack rail pattern)
                    // CRITICAL: Always render empty slots to ensure all units are visible
                    // For the last unit (U1), don't add border-bottom to avoid extra visual space
                    const isLastUnit = u === 1;
                    return (
                      <div
                        key={u}
                        onClick={() => onUnitClick && onUnitClick(u)}
                        className={`h-[36px] ${isLastUnit ? '' : 'border-b border-gray-300 dark:border-gray-600'} flex items-center justify-between px-2 text-[10px] text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 cursor-pointer transition-colors relative`}
                        style={{
                          backgroundImage: `
                          repeating-linear-gradient(
                            90deg,
                            transparent,
                            transparent 2px,
                            rgba(200, 200, 200, 0.1) 2px,
                            rgba(200, 200, 200, 0.1) 4px
                          ),
                          repeating-linear-gradient(
                            90deg,
                            transparent calc(100% - 4px),
                            transparent calc(100% - 2px),
                            rgba(200, 200, 200, 0.1) calc(100% - 2px),
                            rgba(200, 200, 200, 0.1) 100%
                          )
                        `,
                          backgroundSize: '8px 100%, 8px 100%',
                          backgroundPosition: 'left, right',
                          backgroundRepeat: 'no-repeat',
                          marginBottom: isLastUnit ? '0px' : undefined
                        }}
                        title={`Unit ${u} - Available`}
                      >
                        <span className="text-gray-300 dark:text-gray-500 z-10 relative">[ Empty ]</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="text-center mt-1 mb-0 pb-0 font-bold text-gray-700 dark:text-gray-300 text-sm">{rackCode}</div>
          </div>
        </div>

        {/* Right side: Asset List - Shows on Hover (if enabled) */}
        {showAssetListOnHover && rackAssets.length > 0 && (
          <div
            className={`flex-shrink-0 w-64 transition-all duration-200 ease-in-out ${showAssetList
              ? 'opacity-100 translate-x-0 pointer-events-auto'
              : 'opacity-0 -translate-x-4 pointer-events-none overflow-hidden'
              }`}
            onMouseEnter={() => setShowAssetList(true)}
            onMouseLeave={() => setShowAssetList(false)}
          >
            {showAssetList && (
              <div className="bg-card rounded-lg shadow-lg dark:shadow-gray-900 p-3 border border-default sticky top-4">
                <h4 className="text-sm font-semibold text-primary mb-2">Installed Devices ({rackAssets.length})</h4>
                <div className="space-y-1 max-h-[calc(100vh-200px)] overflow-y-auto">
                  {rackAssets
                    .sort((a, b) => {
                      // Sort top-down: highest rack_position_start first (U42 before U1)
                      const aPos = a.rack_position_start || 0;
                      const bPos = b.rack_position_start || 0;
                      return bPos - aPos; // Descending order
                    })
                    .map(asset => (
                      <div
                        key={asset.id}
                        onClick={(e) => {
                          e.stopPropagation(); // Prevent event from bubbling to parent elements
                          if (onAssetClick) {
                            onAssetClick(asset);
                          }
                        }}
                        className="text-xs p-2 bg-subtle hover:bg-table-row-hover rounded cursor-pointer border border-default transition-colors"
                        title={asset.asset_tag ? `Tag: ${asset.asset_tag}` : undefined}
                      >
                        <div className="font-medium text-primary">{getDeviceDisplayName(asset)}</div>
                        {asset.asset_tag && (
                          <div className="text-secondary text-[10px] font-mono">
                            {asset.asset_tag}
                          </div>
                        )}
                        <div className="text-secondary">
                          U{asset.rack_position_start}
                          {asset.rack_position_end && asset.rack_position_end !== asset.rack_position_start
                            ? `-${asset.rack_position_end}`
                            : ''}
                          {asset.height_u && asset.height_u > 1 ? ` (${asset.height_u}U)` : ''}
                        </div>
                        {asset.manufacturer && asset.model && (
                          <div className="text-secondary text-[10px] mt-1">
                            {asset.manufacturer} {asset.model}
                          </div>
                        )}
                        {asset.serial_number && (
                          <div className="text-secondary text-[10px]">
                            SN: {asset.serial_number}
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper function to check if a position is available (for collision detection)
export const isPositionAvailable = (
  rackId: number,
  startU: number,
  heightU: number,
  assets: Asset[],
  excludeAssetId?: number
): boolean => {
  const rackAssets = assets.filter(
    asset => asset.rack_id === rackId && asset.id !== excludeAssetId
  );

  const endU = startU + heightU - 1;

  // Check if any existing asset overlaps with the requested position
  for (const asset of rackAssets) {
    const assetStart = asset.rack_position_start || 0;
    const assetEnd = asset.rack_position_end || assetStart;

    // Check for overlap: [startU, endU] overlaps with [assetStart, assetEnd]
    if (!(endU < assetStart || startU > assetEnd)) {
      return false; // Collision detected
    }
  }

  return true; // Position is available
};

// Helper function to get available positions in a rack
export const getAvailablePositions = (
  rackId: number,
  heightU: number,
  rackSize: number,
  assets: Asset[],
  excludeAssetId?: number
): number[] => {
  const available: number[] = [];

  for (let startU = 1; startU <= rackSize - heightU + 1; startU++) {
    if (isPositionAvailable(rackId, startU, heightU, assets, excludeAssetId)) {
      available.push(startU);
    }
  }

  return available;
};

