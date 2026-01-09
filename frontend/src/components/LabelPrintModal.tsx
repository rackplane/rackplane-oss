// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useCapabilities } from '../contexts/CapabilityContext';

interface Asset {
  id: number;
  asset_tag: string;
  serial_number: string;
  asset_type: string;
  manufacturer: string;
  model: string;
  hostname?: string;
  custom_fields?: {
    quantity?: number;
    [key: string]: any;
  };
}

interface StorageContainer {
  id: number;
  name: string;
  container_type: string;
  barcode?: string;
  datacenter_id?: number;
  room_id?: number;
  location?: string;
}

interface LabelPrintModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: Asset | StorageContainer;
  itemType: 'asset' | 'container';
  labelSize?: '12mm' | '24mm';
}

const LabelPrintModal: React.FC<LabelPrintModalProps> = ({
  isOpen,
  onClose,
  item,
  itemType,
  labelSize: initialLabelSize = '24mm'
}) => {
  const printRef = useRef<HTMLDivElement>(null);
  const [currentInstance, setCurrentInstance] = useState(1);
  const [printAllInstances, setPrintAllInstances] = useState(false);
  const [labelSize, setLabelSize] = useState<'12mm' | '24mm'>(initialLabelSize);

  // Get quantity for bulk items
  const quantity = itemType === 'asset' && (item as Asset).custom_fields?.quantity
    ? (item as Asset).custom_fields!.quantity!
    : 1;

  const { checkCapability } = useCapabilities();

  // State for QR code image URL (fetched with auth)
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');

  // Fetch QR code image with authentication
  useEffect(() => {
    const fetchQRCode = async () => {
      const token = localStorage.getItem('auth_token');
      if (!token) return;

      try {
        const endpoint = itemType === 'asset'
          ? `${API_URL}/api/v1/barcodes/generate/${item.id}`
          : `${API_URL}/api/v1/barcodes/generate-container/${item.id}`;

        const response = await axios.get(endpoint, {
          responseType: 'blob',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const blob = new Blob([response.data], { type: 'image/png' });
        const url = URL.createObjectURL(blob);
        setQrCodeUrl(url);
      } catch (err) {
        logger.error('Error fetching QR code:', err);
      }
    };

    if (isOpen) {
      fetchQRCode();
    }

    return () => {
      if (qrCodeUrl) {
        URL.revokeObjectURL(qrCodeUrl);
      }
    };
  }, [isOpen, item.id, itemType]);

  useEffect(() => {
    if (isOpen) {
      const style = document.createElement('style');
      style.id = 'label-print-styles';
      style.textContent = `
        @media print {
          body {
            margin: 0;
            padding: 0;
          }
          @page {
            size: ${labelSize === '12mm' ? '70mm 12mm' : '70mm 24mm'};
            margin: 0;
          }
        }
      `;
      document.head.appendChild(style);

      return () => {
        const existingStyle = document.getElementById('label-print-styles');
        if (existingStyle) {
          existingStyle.remove();
        }
      };
    }
  }, [isOpen, labelSize]);

  const handlePrint = () => {
    // Use CSS print media query approach instead of DOM manipulation
    // This is safer and doesn't cause memory leaks or event handler issues

    // Get the print container
    const printContainer = printRef.current;
    if (!printContainer) return;

    // Create a style element for print-only display
    const printStyle = document.createElement('style');
    printStyle.id = 'label-print-styles';
    printStyle.textContent = `
      @media print {
        body * {
          visibility: hidden;
        }
        #label-print-container,
        #label-print-container * {
          visibility: visible;
        }
        #label-print-container {
          position: absolute;
          left: 0;
          top: 0;
        }
      }
    `;

    // Add the style, print, then remove it
    document.head.appendChild(printStyle);
    printContainer.id = 'label-print-container';

    window.print();

    // Cleanup after print dialog closes
    setTimeout(() => {
      document.getElementById('label-print-styles')?.remove();
    }, 100);
  };

  const handleQueuePrint = async () => {
    if (!checkCapability('label_printing')) {
      alert('This is a premium feature. Please upgrade to access labels printing.');
      return;
    }
    // This will create print jobs in the queue
    try {
      const printer_ip = localStorage.getItem('brother_printer_ip') || null;
      const token = localStorage.getItem('auth_token') || '';

      if (printAllInstances && quantity > 1) {
        // Queue all instances
        let successCount = 0;
        for (let i = 1; i <= quantity; i++) {
          const jobData = {
            job_type: itemType === 'asset' ? 'asset_label' : 'container_label',
            asset_id: itemType === 'asset' ? item.id : null,
            container_id: itemType === 'container' ? item.id : null,
            label_size: labelSize,
            printer_ip: printer_ip,
            instance: i,
            total_instances: quantity,
            priority: 0
          };

          const response = await axios.post(
            `${API_URL}/api/v1/print-jobs/`,
            jobData,
            {
              headers: {
                'Authorization': token ? `Bearer ${token}` : '',
              }
            }
          );

          if (response.status === 201) {
            successCount++;
          } else {
            logger.error(`Failed to queue instance ${i}:`, response.data);
          }
        }

        alert(`Successfully queued ${successCount} of ${quantity} labels for printing! The print agent will process them automatically.`);
        onClose();
      } else {
        // Queue single instance (current)
        const jobData = {
          job_type: itemType === 'asset' ? 'asset_label' : 'container_label',
          asset_id: itemType === 'asset' ? item.id : null,
          container_id: itemType === 'container' ? item.id : null,
          label_size: labelSize,
          printer_ip: printer_ip,
          instance: currentInstance,
          total_instances: quantity,
          priority: 0
        };

        const response = await axios.post(
          `${API_URL}/api/v1/print-jobs/`,
          jobData,
          {
            headers: {
              'Authorization': token ? `Bearer ${token}` : '',
            }
          }
        );

        if (response.status === 201) {
          alert('Label queued for printing! The print agent will process it automatically.');
          onClose();
        } else {
          alert(`Failed to queue print job: ${response.data?.detail || 'Unknown error'}`);
        }
      }
    } catch (err: any) {
      logger.error('Queue print error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Unknown error';
      alert(`Failed to queue print job: ${errorMsg}`);
    }
  };

  const handleDirectPrint = async () => {
    if (!checkCapability('label_printing')) {
      alert('This is a premium feature. Please upgrade to access direct printing.');
      return;
    }
    // This will send to the backend endpoint for direct printer communication
    try {
      const printer_ip = localStorage.getItem('brother_printer_ip') || null;

      if (!printer_ip) {
        alert('Printer IP address is required for direct printing. Please configure it in the printer settings below.');
        return;
      }

      if (printAllInstances && quantity > 1) {
        // Print all instances sequentially
        const authHeader = axios.defaults.headers.common['Authorization'];
        const token = localStorage.getItem('auth_token') || (typeof authHeader === 'string' ? authHeader.replace('Bearer ', '') : '');
        let successCount = 0;
        for (let i = 1; i <= quantity; i++) {
          const endpoint = itemType === 'asset'
            ? `${API_URL}/api/v1/barcodes/print-label/${item.id}`
            : `${API_URL}/api/v1/barcodes/print-container-label/${item.id}`;

          const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token ? `Bearer ${token}` : '',
            },
            body: JSON.stringify({
              label_size: labelSize,
              printer_ip: printer_ip,
              instance: i,
              total_instances: quantity
            })
          });

          if (response.ok) {
            successCount++;
          } else {
            const error = await response.json();
            logger.error(`Failed to print instance ${i}:`, error);
          }

          // Small delay between prints to avoid overwhelming the printer
          if (i < quantity) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }

        alert(`Successfully sent ${successCount} of ${quantity} labels to printer!`);
        onClose();
      } else {
        // Print single instance (current)
        const endpoint = itemType === 'asset'
          ? `${API_URL}/api/v1/barcodes/print-label/${item.id}`
          : `${API_URL}/api/v1/barcodes/print-container-label/${item.id}`;

        // Get auth token from localStorage or axios defaults
        const authHeader = axios.defaults.headers.common['Authorization'];
        const token = localStorage.getItem('auth_token') || (typeof authHeader === 'string' ? authHeader.replace('Bearer ', '') : '');

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : '',
          },
          body: JSON.stringify({
            label_size: labelSize,
            printer_ip: printer_ip,
            instance: currentInstance,
            total_instances: quantity
          })
        });

        if (response.ok) {
          alert('Label sent to printer successfully!');
          onClose();
        } else {
          const error = await response.json();
          alert(`Failed to print: ${error.detail || 'Unknown error'}`);
        }
      }
    } catch (err: any) {
      logger.error('Print error:', err);
      alert('Failed to send to printer. Using browser print instead.');
      handlePrint();
    }
  };

  if (!isOpen) return null;

  const label12mmStyle = {
    width: '70mm',
    height: '12mm',
    display: 'flex',
    alignItems: 'center',
    padding: '1mm',
    backgroundColor: 'white',
    border: '1px solid #000',
    boxSizing: 'border-box' as const,
  };

  const label24mmStyle = {
    width: '70mm',
    height: '24mm',
    display: 'flex',
    alignItems: 'center',
    padding: '2mm',
    backgroundColor: 'white',
    border: '1px solid #000',
    boxSizing: 'border-box' as const,
  };

  const labelStyle = labelSize === '12mm' ? label12mmStyle : label24mmStyle;
  const qrSize = labelSize === '12mm' ? '10mm' : '18mm';
  const fontSize = labelSize === '12mm' ? '5pt' : '7pt';
  const fontSizeSmall = labelSize === '12mm' ? '4pt' : '6pt';

  // Generate unique serial number for bulk items
  const getUniqueSerialNumber = (baseSerial: string, instance: number, total: number): string => {
    if (total === 1) return baseSerial;
    const padding = total >= 100 ? 3 : 2;
    const instanceStr = instance.toString().padStart(padding, '0');
    return `${baseSerial}-${instanceStr}`;
  };

  // Render label content based on item type and instance number
  const renderLabelContent = (instanceNumber: number = currentInstance) => {
    if (itemType === 'asset') {
      const asset = item as Asset;
      const uniqueSerialNumber = getUniqueSerialNumber(asset.serial_number, instanceNumber, quantity);
      const showInstanceInfo = quantity > 1;

      return (
        <>
          <div style={{
            fontWeight: 'bold',
            fontSize: fontSize,
            fontFamily: 'Arial, sans-serif',
            marginBottom: '1mm',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {asset.asset_tag}
            {showInstanceInfo && ` #${instanceNumber}`}
          </div>
          <div style={{
            fontSize: fontSizeSmall,
            fontFamily: 'Arial, sans-serif',
            marginBottom: '0.5mm',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {asset.manufacturer} {asset.model}
          </div>
          <div style={{
            fontSize: fontSizeSmall,
            fontFamily: 'Arial, sans-serif',
            color: '#555',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            S/N: {uniqueSerialNumber}
          </div>
          {showInstanceInfo && (
            <div style={{
              fontSize: fontSizeSmall,
              fontFamily: 'Arial, sans-serif',
              color: '#555',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              Unit {instanceNumber} of {quantity}
            </div>
          )}
          {asset.hostname && (
            <div style={{
              fontSize: fontSizeSmall,
              fontFamily: 'Arial, sans-serif',
              color: '#555',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {asset.hostname}
            </div>
          )}
        </>
      );
    } else {
      const container = item as StorageContainer;
      return (
        <>
          <div style={{
            fontWeight: 'bold',
            fontSize: fontSize,
            fontFamily: 'Arial, sans-serif',
            marginBottom: '1mm',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {container.name}
          </div>
          <div style={{
            fontSize: fontSizeSmall,
            fontFamily: 'Arial, sans-serif',
            marginBottom: '0.5mm',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            textTransform: 'capitalize'
          }}>
            {container.container_type}
          </div>
          {container.barcode && (
            <div style={{
              fontSize: fontSizeSmall,
              fontFamily: 'Arial, sans-serif',
              color: '#555',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              Barcode: {container.barcode}
            </div>
          )}
          {container.location && (
            <div style={{
              fontSize: fontSizeSmall,
              fontFamily: 'Arial, sans-serif',
              color: '#555',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {container.location}
            </div>
          )}
        </>
      );
    }
  };

  // Render a single label for a specific instance
  const renderSingleLabel = (instanceNumber: number, isPreview: boolean = false) => {
    // Only add page break if printing all instances AND not the last one
    const needsPageBreak = printAllInstances && quantity > 1 && instanceNumber < quantity;

    return (
      <div
        key={`label-${instanceNumber}`}
        style={{
          ...labelStyle,
          pageBreakAfter: needsPageBreak ? 'always' : 'auto'
        }}
      >
        {/* QR Code */}
        <div style={{ marginRight: '3mm', flexShrink: 0 }}>
          <img
            src={qrCodeUrl}
            alt="QR Code"
            style={{
              width: qrSize,
              height: qrSize,
              display: 'block'
            }}
          />
        </div>

        {/* Item Information */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          overflow: 'hidden',
          flex: 1
        }}>
          {renderLabelContent(instanceNumber)}
        </div>
      </div>
    );
  };

  const itemLabel = itemType === 'asset' ? 'Asset' : 'Storage Container';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
      <div className="bg-card rounded-lg shadow-xl max-w-3xl w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Print {itemLabel} Label</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-2">
            Label preview optimized for Brother PT-E550W
          </p>
          <div className="flex gap-4 mb-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="labelSize"
                value="12mm"
                checked={labelSize === '12mm'}
                onChange={(e) => setLabelSize(e.target.value as '12mm' | '24mm')}
                className="mr-2"
              />
              <span className="text-sm">12mm (0.47")</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="labelSize"
                value="24mm"
                checked={labelSize === '24mm'}
                onChange={(e) => setLabelSize(e.target.value as '12mm' | '24mm')}
                className="mr-2"
              />
              <span className="text-sm">24mm (0.94")</span>
            </label>
          </div>

          {/* Instance selector for bulk items */}
          {quantity > 1 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold text-yellow-900">
                  Bulk Item: {quantity} units
                </div>
                <div className="text-sm text-yellow-700">
                  Showing: Unit {currentInstance} of {quantity}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setCurrentInstance(Math.max(1, currentInstance - 1))}
                  disabled={currentInstance === 1}
                  className="px-3 py-1 bg-card border border-yellow-300 rounded hover:bg-yellow-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  ← Previous
                </button>
                <div className="flex-1 text-center text-sm text-yellow-700">
                  Each unit will have a unique serial number (e.g., {getUniqueSerialNumber((item as Asset).serial_number, 1, quantity)})
                </div>
                <button
                  onClick={() => setCurrentInstance(Math.min(quantity, currentInstance + 1))}
                  disabled={currentInstance === quantity}
                  className="px-3 py-1 bg-card border border-yellow-300 rounded hover:bg-yellow-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  Next →
                </button>
              </div>
              <div className="mt-3">
                <label className="flex items-center text-sm text-yellow-900">
                  <input
                    type="checkbox"
                    checked={printAllInstances}
                    onChange={(e) => setPrintAllInstances(e.target.checked)}
                    className="mr-2"
                  />
                  Print all {quantity} labels at once (recommended)
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Label Preview */}
        <div className="bg-subtle-card p-8 rounded-lg mb-6 flex justify-center">
          <div className="print-labels-container" ref={printRef}>
            {printAllInstances && quantity > 1 ? (
              // Print all instances - render them all
              Array.from({ length: quantity }, (_, i) => i + 1).map((instance) =>
                renderSingleLabel(instance, true)
              )
            ) : (
              // Print single instance only
              renderSingleLabel(currentInstance, true)
            )}
          </div>
        </div>

        {/* Print Options */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <h3 className="font-semibold text-blue-900 mb-2">Print Options</h3>
          <p className="text-sm text-blue-800 mb-3">
            <strong>Queue for Printing:</strong> Adds the label to the print queue. A print agent will automatically process it.
            <br />
            <strong>Print via Browser:</strong> Opens your browser's print dialog for manual printing.
          </p>
          <details className="text-sm text-blue-700">
            <summary className="cursor-pointer font-medium mb-2">Printer IP (Optional)</summary>
            <div className="pl-4 mt-2 space-y-2">
              <p>To specify a specific printer for queued jobs:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Ensure your printer is connected to the network</li>
                <li>Find your printer's IP address (check printer settings)</li>
                <li>Enter the IP address below (optional - agents can auto-detect printers):</li>
              </ol>
              <input
                type="text"
                placeholder="e.g., 192.168.1.100 (optional)"
                defaultValue={localStorage.getItem('brother_printer_ip') || ''}
                onChange={(e) => localStorage.setItem('brother_printer_ip', e.target.value)}
                className="border border-blue-300 rounded px-3 py-2 w-full text-sm mt-2"
              />
            </div>
          </details>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition"
          >
            Cancel
          </button>
          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            Print via Browser
          </button>

          {checkCapability('label_printing') ? (
            <>
              <button
                onClick={handleQueuePrint}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition"
              >
                Queue for Printing
              </button>
              {localStorage.getItem('brother_printer_ip') && (
                <button
                  onClick={handleDirectPrint}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition"
                >
                  Send to Printer Directly
                </button>
              )}
            </>
          ) : (
            <div className="flex items-center gap-2 px-3 bg-gray-100 border border-gray-300 rounded text-gray-500 text-sm">
              <span role="img" aria-label="premium">🔒</span>
              <span>Premium Printing Disabled</span>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-500 mt-4">
          <strong>Print via Browser:</strong> Opens your browser's print dialog for manual printing.
          <br />
          <strong>Queue / Direct (Premium):</strong> Automatic label printing via print agents or direct IP.
        </p>
      </div>
    </div>
  );
};

export default LabelPrintModal;
