// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useCapabilities } from '../contexts/CapabilityContext';

export interface OCRResult {
  raw_text: string;
  parsed_data: {
    serial_number?: string;
    model?: string;
    manufacturer?: string;
    asset_tag?: string;
    part_number?: string;
    mac_address?: string;
    hostname?: string;
  };
  confidence: string;
  suggestions: string[];
  scan_id?: number;  // For Cloud OCR escalation
  source?: 'tesseract' | 'cloud';  // Which OCR engine was used
}

interface ImageUploadOCRProps {
  onOCRComplete?: (ocrResult: OCRResult, imageUrl: string) => void;
  onImageSelect?: (imageUrl: string) => void;
  onClear?: () => void;
}

const ImageUploadOCR: React.FC<ImageUploadOCRProps> = ({ onOCRComplete, onImageSelect, onClear }) => {
  const [processing, setProcessing] = useState(false);
  const [cloudProcessing, setCloudProcessing] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cloudError, setCloudError] = useState<string | null>(null);
  const [creditsRemaining, setCreditsRemaining] = useState<number | null>(null);
  const [editedData, setEditedData] = useState<Record<string, string>>({});
  const [correctionSubmitted, setCorrectionSubmitted] = useState(false);
  const [submittingCorrection, setSubmittingCorrection] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const { capabilities, checkCapability } = useCapabilities();
  const isPremium = capabilities?.build_mode === 'premium';

  // Get confidence color
  const getConfidenceColor = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case 'high': return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border-green-300 dark:border-green-700';
      case 'medium': return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 border-yellow-300 dark:border-yellow-700';
      case 'low': return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700';
      default: return 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-700';
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image file too large (max 10MB)');
      return;
    }

    setError(null);
    setCloudError(null);
    setProcessing(true);
    setImageFile(file);

    try {
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        const preview = e.target?.result as string;
        setImagePreview(preview);
        if (onImageSelect) {
          onImageSelect(preview);
        }
      };
      reader.readAsDataURL(file);

      // Skip OCR processing in OSS mode
      if (!isPremium) {
        setProcessing(false);
        return;
      }

      // First try the new OCR proxy endpoint (services.rackplane.com style)
      const formData = new FormData();
      formData.append('image', file);

      let response;
      try {
        // Try new /api/v1/ocr/tesseract endpoint first
        response = await axios.post(`${API_URL}/api/v1/ocr/tesseract`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        // Map response to OCRResult format
        const result: OCRResult = {
          raw_text: response.data.raw_text || '',
          parsed_data: response.data.parsed_data || {},
          confidence: response.data.confidence || 'medium',
          suggestions: response.data.suggestions || [],
          scan_id: response.data.scan_id,
          source: 'tesseract'
        };

        setOcrResult(result);
        if (onOCRComplete) {
          onOCRComplete(result, imagePreview || '');
        }
      } catch (ocrProxyError: any) {
        // Fallback to legacy endpoint
        logger.debug('OCR proxy not available, using legacy endpoint');
        response = await axios.post(`${API_URL}/api/v1/images/process-with-vendor-lookup?auto_fetch_vendor_data=false`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        if (response.data.success || response.data.ocr_results) {
          const ocrData = response.data.ocr_results || response.data;
          const result: OCRResult = {
            raw_text: ocrData.raw_text || '',
            parsed_data: ocrData.parsed_data || {},
            confidence: ocrData.confidence || 'medium',
            suggestions: ocrData.suggestions || [],
            source: 'tesseract'
          };

          setOcrResult(result);
          if (onOCRComplete) {
            onOCRComplete(result, response.data.image_preview || imagePreview || '');
          }
        }
      }
    } catch (err: any) {
      logger.error('Image processing failed:', err);
      setError(err.response?.data?.detail || 'Failed to process image');
    } finally {
      setProcessing(false);
    }
  };

  // Try Cloud OCR for better results
  // useCapabilities hook already pulled at top

  const tryCloudOCR = async () => {
    if (!imageFile) {
      setCloudError('No image available for Cloud OCR');
      return;
    }

    if (!checkCapability('ocr_cloud')) {
      setCloudError('Cloud OCR is a premium feature. Please upgrade your plan to access this capability.');
      return;
    }

    setCloudProcessing(true);
    setCloudError(null);

    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await axios.post(`${API_URL}/api/v1/ocr/cloud`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const result: OCRResult = {
        raw_text: response.data.raw_text || '',
        parsed_data: response.data.parsed_data || {},
        confidence: response.data.confidence || 'high',
        suggestions: response.data.suggestions || [],
        scan_id: response.data.scan_id,
        source: 'cloud'
      };

      setOcrResult(result);
      // Capture credits remaining from response
      if (response.data.credits_remaining !== undefined) {
        setCreditsRemaining(response.data.credits_remaining);
      }
      // Initialize editable data with parsed data
      setEditedData(response.data.parsed_data || {});
      setCorrectionSubmitted(false);
      if (onOCRComplete && imagePreview) {
        onOCRComplete(result, imagePreview);
      }
    } catch (err: any) {
      logger.error('Cloud OCR failed:', err);
      // 402/403 should be caught by capability check, but keeping as fallback
      if (err.response?.status === 402) {
        setCloudError('Cloud OCR requires credits. Add credits in Settings → RackPlane Cloud Services.');
      } else if (err.response?.status === 403) {
        setCloudError('Cloud OCR not enabled. Connect to RackPlane Cloud in Settings.');
      } else {
        setCloudError(err.response?.data?.detail || 'Cloud OCR failed. Try again later.');
      }
    } finally {
      setCloudProcessing(false);
    }
  };

  const handleCameraCapture = async (event: React.ChangeEvent<HTMLInputElement>) => {
    await handleFileSelect(event);
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const triggerCameraCapture = () => {
    cameraInputRef.current?.click();
  };

  const clearImage = () => {
    setImagePreview(null);
    setImageFile(null);
    setOcrResult(null);
    setError(null);
    setCloudError(null);
    setCreditsRemaining(null);
    setEditedData({});
    setCorrectionSubmitted(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (onClear) {
      onClear();
    }
  };

  // Submit user corrections for ML training
  const submitCorrection = async () => {
    if (!ocrResult?.scan_id) {
      setCloudError('No scan ID available for correction');
      return;
    }

    setSubmittingCorrection(true);
    try {
      await axios.patch(`${API_URL}/api/v1/images/scan/${ocrResult.scan_id}/correct`, {
        correct_serial: editedData.serial_number,
        correct_model: editedData.model,
        correct_manufacturer: editedData.manufacturer,
        correct_part_number: editedData.part_number,
        correct_asset_tag: editedData.asset_tag,
      });
      setCorrectionSubmitted(true);
      setCloudError(null);
    } catch (err: any) {
      logger.error('Correction submission failed:', err);
      setCloudError(err.response?.data?.detail || 'Failed to submit correction');
    } finally {
      setSubmittingCorrection(false);
    }
  };

  // Check if data has been edited
  const hasEdits = () => {
    if (!ocrResult?.parsed_data) return false;
    return Object.keys(editedData).some(key =>
      editedData[key] !== (ocrResult.parsed_data as Record<string, string>)[key]
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleCameraCapture}
          className="hidden"
        />

        <button
          type="button"
          onClick={triggerFileUpload}
          className="btn-secondary flex items-center gap-2"
          disabled={processing || cloudProcessing}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Upload Image
        </button>

        <button
          type="button"
          onClick={triggerCameraCapture}
          className="btn-secondary flex items-center gap-2"
          disabled={processing || cloudProcessing}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Take Photo
        </button>

        {imagePreview && (
          <button
            type="button"
            onClick={clearImage}
            className="btn-secondary"
            disabled={processing || cloudProcessing}
          >
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {processing && isPremium && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <span className="text-blue-700">Processing image with Tesseract OCR...</span>
          </div>
        </div>
      )}

      {cloudProcessing && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
            <span className="text-purple-700">Processing with Cloud OCR (Google Vision)...</span>
          </div>
        </div>
      )}

      {imagePreview && (
        <div className="space-y-4">
          <div className="border border-default rounded-lg p-3 bg-card">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Image Preview</h4>
            <img
              src={imagePreview}
              alt="Preview"
              className="max-w-full h-auto max-h-64 rounded border border-gray-200 dark:border-gray-600"
            />
          </div>

          {isPremium && ocrResult && (
            <div className="space-y-3">
              {/* Confidence Badge & Cloud OCR Button */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getConfidenceColor(ocrResult.confidence)}`}>
                    {ocrResult.source === 'cloud' ? '☁️ Cloud OCR' : '🔍 Tesseract'} • {ocrResult.confidence.charAt(0).toUpperCase() + ocrResult.confidence.slice(1)} Confidence
                  </span>
                  {/* Credits remaining badge */}
                  {creditsRemaining !== null && (
                    <span className="px-3 py-1 rounded-full text-xs font-medium border bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border-blue-300 dark:border-blue-700">
                      💳 {creditsRemaining} credits remaining
                    </span>
                  )}
                </div>

                {/* Show Cloud OCR button for low/medium confidence Tesseract results */}
                {ocrResult.source !== 'cloud' && (ocrResult.confidence === 'low' || ocrResult.confidence === 'medium') && (
                  <button
                    type="button"
                    onClick={tryCloudOCR}
                    disabled={cloudProcessing}
                    className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50"
                  >
                    <span>🤖</span>
                    Try Cloud OCR
                  </button>
                )}
              </div>

              {cloudError && (
                <div className="p-3 bg-yellow-50 border border-yellow-300 text-yellow-800 rounded text-sm">
                  {cloudError}
                </div>
              )}

              {/* Suggestions */}
              {ocrResult.suggestions.length > 0 && (
                <div className="p-4 bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-lg">
                  <h4 className="text-sm font-semibold text-green-800 dark:text-green-200 mb-2">Detected Information</h4>
                  <ul className="space-y-1">
                    {ocrResult.suggestions.map((suggestion, index) => (
                      <li key={index} className="text-sm text-green-700 dark:text-green-300 flex items-start gap-2">
                        <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Editable Parsed Data */}
              {Object.keys(ocrResult.parsed_data).some(key => ocrResult.parsed_data[key as keyof typeof ocrResult.parsed_data]) && (
                <div className="border border-default rounded-lg p-4 bg-card">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200">Extracted Fields</h4>
                    {hasEdits() && !correctionSubmitted && (
                      <span className="text-xs text-orange-600 dark:text-orange-400">✏️ Edited</span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(ocrResult.parsed_data).map(([key, value]) => (
                      value && (
                        <div key={key} className="text-sm">
                          <label className="text-gray-600 dark:text-gray-400 capitalize block mb-1">
                            {key.replace('_', ' ')}
                          </label>
                          <input
                            type="text"
                            value={editedData[key] || value}
                            onChange={(e) => setEditedData({ ...editedData, [key]: e.target.value })}
                            className="w-full px-2 py-1 text-sm font-mono border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                      )
                    ))}
                  </div>

                  {/* Submit Correction Button */}
                  {ocrResult.scan_id && (
                    <div className="mt-4 flex items-center gap-3">
                      {correctionSubmitted ? (
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Correction submitted for review
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={submitCorrection}
                          disabled={submittingCorrection || !hasEdits()}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {submittingCorrection ? 'Submitting...' : '📤 Submit Correction'}
                        </button>
                      )}
                      {!correctionSubmitted && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Help improve OCR accuracy. Credits awarded after review.
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Raw OCR Text */}
              {ocrResult.raw_text && (
                <details className="border border-default rounded-lg p-4 bg-card">
                  <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
                    View Raw OCR Text
                  </summary>
                  <pre className="mt-3 text-xs text-secondary whitespace-pre-wrap font-mono bg-subtle-card p-3 rounded">
                    {ocrResult.raw_text}
                  </pre>
                </details>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageUploadOCR;
