// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Html5QrcodeScanner, Html5QrcodeScanType } from 'html5-qrcode';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import logger from '../utils/logger';
import PortSelectorModal from './PortSelectorModal';
import CompatibilityWarning, { CompatibilityResult } from './CompatibilityWarning';
import ManualCableConnection from './ManualCableConnection';

interface Asset {
  id: number;
  asset_tag: string;
  asset_type: string;
  manufacturer?: string;
  model?: string;
}

interface ConnectionResponse {
  connection: {
    id: number;
    cable_asset_id: number;
    port_id?: number;  // Phase 2: port-based
    device_asset_id?: number;  // Deprecated
    port_label?: string | null;
    end_label: string;
  };
  end_label: string;
  message: string;
  // Phase 3: Compatibility result
  compatibility?: CompatibilityResult;
}

type ScannerState = 'idle' | 'cable_active';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

const CableScanner: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [state, setState] = useState<ScannerState>('idle');
  const [activeCable, setActiveCable] = useState<Asset | null>(null);
  const [scanInput, setScanInput] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [showCamera, setShowCamera] = useState(false);
  const scannerRef = useRef<Html5QrcodeScanner | null>(null);

  // Phase 2: Port selection state
  const [showPortSelector, setShowPortSelector] = useState(false);
  const [targetDevice, setTargetDevice] = useState<Asset | null>(null);

  // Phase 3: Compatibility warning state
  const [compatibilityResult, setCompatibilityResult] = useState<CompatibilityResult | null>(null);

  // Tab state: 'scan' or 'manual'
  const [activeTab, setActiveTab] = useState<'scan' | 'manual'>('scan');

  // Auto-dismiss toasts after 5 seconds
  useEffect(() => {
    toasts.forEach(toast => {
      const timer = setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, 5000);
      return () => clearTimeout(timer);
    });
  }, [toasts]);

  // Initialize camera scanner when showCamera is true
  useEffect(() => {
    if (!showCamera) {
      // Clean up scanner when closing
      if (scannerRef.current) {
        scannerRef.current.clear().catch((err: any) => {
          logger.error('Error clearing scanner:', err);
        });
        scannerRef.current = null;
      }
      return;
    }

    const config = {
      fps: 10,
      qrbox: { width: 250, height: 250 },
      supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
      rememberLastUsedCamera: true,
    };

    const scanner = new Html5QrcodeScanner('cable-qr-reader', config, false);

    const onScanSuccess = (decodedText: string, result: any) => {
      logger.debug('QR Code scanned:', decodedText);
      // Close camera and process the scan
      setShowCamera(false);
      handleScan(decodedText);
    };

    const onScanError = (errorMessage: string) => {
      // Ignore frequent scanning errors
      if (errorMessage.includes('NotFoundException')) {
        return;
      }
      logger.warn('Scan error:', errorMessage);
    };

    scanner.render(onScanSuccess, onScanError);

    scannerRef.current = scanner;

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch((err: any) => {
          logger.error('Error clearing scanner:', err);
        });
        scannerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCamera]);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const fetchAssetById = async (assetId: number): Promise<Asset | null> => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/assets/${assetId}`);
      return response.data;
    } catch (error: any) {
      logger.error('Error fetching asset:', error);
      showToast(`Failed to fetch asset: ${error.response?.data?.detail || error.message}`, 'error');
      return null;
    }
  };

  const handleScan = async (scannedData: string) => {
    if (!isAuthenticated) {
      showToast('Please log in to use the cable scanner', 'error');
      return;
    }

    setLoading(true);
    try {
      // Parse scanned data - could be JSON with {id: X} or just an ID
      let assetId: number;
      try {
        const parsed = JSON.parse(scannedData);
        assetId = parsed.id || parsed;
      } catch {
        // If not JSON, assume it's just the ID
        assetId = parseInt(scannedData, 10);
      }

      if (isNaN(assetId)) {
        showToast('Invalid scan data. Please scan a valid asset QR code.', 'error');
        setLoading(false);
        return;
      }

      const asset = await fetchAssetById(assetId);
      if (!asset) {
        setLoading(false);
        return;
      }

      // State machine logic
      if (state === 'idle') {
        // State 1: Check if scanned asset is a cable
        if (asset.asset_type.toLowerCase().includes('cable') ||
          asset.asset_type.toLowerCase().includes('cable_device')) {
          setActiveCable(asset);
          setState('cable_active');
          showToast(`Cable "${asset.asset_tag}" selected. Now scan the device to connect.`, 'info');
        } else {
          showToast('Please scan a cable first. This asset is not a cable type.', 'error');
        }
      } else if (state === 'cable_active') {
        // State 2: Show port selector for the device
        if (!activeCable) {
          showToast('Error: Active cable lost. Please start over.', 'error');
          setState('idle');
          setLoading(false);
          return;
        }

        // Prevent connecting cable to itself
        if (asset.id === activeCable.id) {
          showToast('Cannot connect a cable to itself. Please scan a different device.', 'error');
          setLoading(false);
          return;
        }

        // Phase 2: Show port selector modal
        setTargetDevice(asset);
        setShowPortSelector(true);
      }

      setScanInput('');
    } catch (error: any) {
      logger.error('Error in handleScan:', error);
      showToast(`Error: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Phase 2: Handle port selection and connect
  const handlePortSelect = async (portId: number, portLabel: string) => {
    if (!activeCable || !targetDevice) {
      showToast('Error: Cable or device lost. Please start over.', 'error');
      handleCancel();
      return;
    }

    setShowPortSelector(false);
    setLoading(true);
    setCompatibilityResult(null);  // Clear previous results

    try {
      const response = await axios.post<ConnectionResponse>(
        `${API_URL}/api/v1/connections/connect`,
        {
          cable_id: activeCable.id,
          port_id: portId  // Phase 2: Use port_id
        }
      );

      const { end_label, message, compatibility } = response.data;

      // Phase 3: Show compatibility warning if present
      if (compatibility) {
        setCompatibilityResult(compatibility);
        // Auto-dismiss after 8 seconds for non-incompatible levels
        if (compatibility.level !== 'incompatible') {
          setTimeout(() => setCompatibilityResult(null), 8000);
        }
      }

      if (end_label === 'A') {
        showToast(message, 'info');
      } else if (end_label === 'B') {
        showToast(message, 'success');
        setActiveCable(null);
        setState('idle');
      }
      setTargetDevice(null);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to connect cable';
      showToast(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (scanInput.trim()) {
      handleScan(scanInput.trim());
    }
  };

  const handleCancel = () => {
    setActiveCable(null);
    setTargetDevice(null);
    setShowPortSelector(false);
    setState('idle');
    setScanInput('');
    showToast('Cable connection cancelled', 'info');
  };

  return (
    <div className="min-h-screen bg-page p-4">
      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg max-w-md animate-slide-in ${toast.type === 'success'
              ? 'bg-green-500 text-white'
              : toast.type === 'error'
                ? 'bg-red-500 text-white'
                : 'bg-blue-500 text-white'
              }`}
          >
            <div className="flex items-center justify-between">
              <span>{toast.message}</span>
              <button
                onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
                className="ml-4 text-white hover:text-gray-200"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Phase 3: Compatibility Warning Display */}
      {compatibilityResult && (
        <div className="fixed top-20 right-4 z-40 max-w-md animate-slide-in">
          <CompatibilityWarning
            result={compatibilityResult}
            onDismiss={() => setCompatibilityResult(null)}
          />
        </div>
      )}

      {/* Sticky Header - Active Cable Indicator */}
      {activeCable && (
        <div className="sticky top-0 z-40 bg-blue-600 text-white p-4 rounded-lg shadow-lg mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-700 rounded-full p-2">
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                  />
                </svg>
              </div>
              <div>
                <p className="font-semibold">Active Cable: {activeCable.asset_tag}</p>
                <p className="text-sm text-blue-200">
                  {activeCable.manufacturer} {activeCable.model}
                </p>
                <p className="text-xs text-blue-300 mt-1">
                  {state === 'cable_active' && !activeCable
                    ? 'Waiting for first connection...'
                    : 'Scan the destination device'}
                </p>
              </div>
            </div>
            <button
              onClick={handleCancel}
              className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-4xl mx-auto">
        <div className="bg-card rounded-lg shadow-lg">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setActiveTab('scan')}
              className={`flex-1 py-3 px-4 text-center font-medium transition-colors ${activeTab === 'scan'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
            >
              📷 Scan QR Code
            </button>
            <button
              onClick={() => setActiveTab('manual')}
              className={`flex-1 py-3 px-4 text-center font-medium transition-colors ${activeTab === 'manual'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
            >
              🔧 Manual Connection
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'manual' ? (
            <ManualCableConnection />
          ) : (
            <div className="p-6">
              <h1 className="text-3xl font-bold text-gray-800 mb-2">Cable Connection Scanner</h1>
              <p className="text-gray-600 mb-6">
                Connect cables to devices by scanning QR codes. Start by scanning a cable, then scan the devices at each end.
              </p>

              {/* Scanner Input Form */}
              <form onSubmit={handleManualSubmit} className="space-y-4">
                <div>
                  <label htmlFor="scan-input" className="block text-sm font-medium text-gray-700 mb-2">
                    Scan Asset QR Code
                  </label>
                  <div className="flex space-x-2">
                    <input
                      id="scan-input"
                      type="text"
                      value={scanInput}
                      onChange={(e) => setScanInput(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && scanInput.trim() && !loading) {
                          handleManualSubmit(e);
                        }
                      }}
                      placeholder="Enter asset ID or scan QR code"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={loading}
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={() => setShowCamera(true)}
                      disabled={loading}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors flex items-center space-x-2"
                      title="Open camera scanner"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span>Camera</span>
                    </button>
                    <button
                      type="submit"
                      disabled={loading || !scanInput.trim()}
                      className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${loading || !scanInput.trim()
                        ? 'bg-gray-400 cursor-not-allowed text-gray-200'
                        : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-md hover:shadow-lg'
                        }`}
                      title={!scanInput.trim() ? 'Enter an asset ID to scan' : 'Click to scan asset'}
                    >
                      {loading ? 'Processing...' : 'Scan'}
                    </button>
                  </div>
                  {scanInput.trim() && (
                    <p className="text-xs text-green-600 mt-1">✓ Ready to scan</p>
                  )}
                </div>
              </form>

              {/* State Indicator */}
              <div className="mt-6 p-4 bg-subtle-card rounded-lg">
                <div className="flex items-center space-x-2">
                  <div
                    className={`w-3 h-3 rounded-full ${state === 'idle' ? 'bg-gray-400' : 'bg-green-500 animate-pulse'
                      }`}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {state === 'idle'
                      ? 'Idle - Scan a cable to begin'
                      : `Active - Cable "${activeCable?.asset_tag}" ready for connection`}
                  </span>
                </div>
              </div>

              {/* Instructions */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="font-semibold text-blue-900 mb-2">How to use:</h3>
                <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
                  <li>Scan or enter a cable asset ID</li>
                  <li>Scan the device to connect to</li>
                  <li>Select the port from the port selector</li>
                  <li>Walk to the other end and repeat for End B</li>
                  <li>The circuit will be complete when both ends are connected</li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Port Selector Modal - Phase 2 */}
      {showPortSelector && targetDevice && (
        <PortSelectorModal
          isOpen={showPortSelector}
          deviceId={targetDevice.id}
          deviceName={targetDevice.asset_tag}
          onSelect={handlePortSelect}
          onCancel={() => {
            setShowPortSelector(false);
            setTargetDevice(null);
          }}
        />
      )}

      {/* Camera Scanner Modal */}
      {showCamera && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-900">Scan QR Code</h2>
              <button
                onClick={() => setShowCamera(false)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                Position the QR code within the camera view. The scanner will automatically detect and read it.
              </p>
              {activeCable && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>Active Cable:</strong> {activeCable.asset_tag} - {activeCable.manufacturer} {activeCable.model}
                  </p>
                </div>
              )}
            </div>

            <div id="cable-qr-reader" className="w-full"></div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setShowCamera(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add CSS for toast animation */}
      <style>{`
        @keyframes slide-in {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default CableScanner;

