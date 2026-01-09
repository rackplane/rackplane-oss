import React, { useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface FSOrderImportModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const FSOrderImportModal: React.FC<FSOrderImportModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [mode, setMode] = useState<'order_id' | 'invoice_pdf'>('order_id');
    const [orderId, setOrderId] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<{ message: string; products_found?: number; assets_created?: number } | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [previewData, setPreviewData] = useState<any | null>(null);

    if (!isOpen) return null;

    const handleImportOrderId = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!orderId.trim()) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
            const response = await axios.post(
                `${API_URL}/api/v1/fs/order/import`,
                null,
                {
                    params: { order_id: orderId.trim() },
                    headers
                }
            );

            setResult(response.data);
            if (response.data.products_found > 0) {
                setTimeout(() => {
                    onSuccess();
                    onClose();
                }, 2000);
            }
        } catch (err: any) {
            logger.error('Error importing FS order:', err);
            if (err.response?.status === 429) {
                setError('Daily or Hourly API rate limit reached. Please try again later.');
            } else {
                setError(err.response?.data?.detail || 'Failed to import order.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setPreviewData(null);
            setError(null);
            setResult(null);
        }
    };

    const handlePreviewInvoice = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const headers = {
                Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
                'Content-Type': 'multipart/form-data'
            };

            // Preview only (create_assets=false)
            const response = await axios.post(
                `${API_URL}/api/v1/fs/invoice/parse?create_assets=false`,
                formData,
                { headers }
            );

            if (response.data.success) {
                setPreviewData(response.data);
            } else {
                setError(response.data.message || 'Failed to parse invoice');
            }
        } catch (err: any) {
            logger.error('Error parsing invoice:', err);
            setError(err.response?.data?.detail || 'Failed to parse invoice file.');
        } finally {
            setLoading(false);
        }
    };

    const handleImportInvoice = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const headers = {
                Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
                'Content-Type': 'multipart/form-data'
            };

            // Import and create assets (create_assets=true)
            const response = await axios.post(
                `${API_URL}/api/v1/fs/invoice/parse?create_assets=true`,
                formData,
                { headers }
            );

            if (response.data.success) {
                setResult({
                    message: response.data.message,
                    products_found: response.data.products?.length || 0,
                    assets_created: response.data.assets_created || 0
                });
                if (response.data.assets_created > 0) {
                    setTimeout(() => {
                        onSuccess();
                        onClose();
                    }, 2500);
                }
            } else {
                setError(response.data.message || 'Failed to import invoice');
            }
        } catch (err: any) {
            logger.error('Error importing invoice:', err);
            setError(err.response?.data?.detail || 'Failed to import invoice.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-primary">Import from FS.com</h2>
                        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Tabs */}
                    <div className="flex border-b border-border-color mb-6">
                        <button
                            className={`pb-2 px-4 font-medium transition-colors ${mode === 'order_id'
                                ? 'border-b-2 border-blue-600 text-blue-600'
                                : 'text-muted-foreground hover:text-foreground'}`}
                            onClick={() => setMode('order_id')}
                        >
                            By Order ID
                        </button>
                        <button
                            className={`pb-2 px-4 font-medium transition-colors ${mode === 'invoice_pdf'
                                ? 'border-b-2 border-blue-600 text-blue-600'
                                : 'text-muted-foreground hover:text-foreground'}`}
                            onClick={() => setMode('invoice_pdf')}
                        >
                            By Invoice PDF
                        </button>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 rounded text-sm">
                            {error}
                        </div>
                    )}

                    {result && (
                        <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-200 rounded text-sm">
                            <p className="font-bold">Success!</p>
                            <p>{result.message}</p>
                            {result.assets_created !== undefined && (
                                <p>Created {result.assets_created} assets.</p>
                            )}
                        </div>
                    )}

                    {mode === 'order_id' ? (
                        <form onSubmit={handleImportOrderId}>
                            <p className="text-sm text-muted-foreground mb-4">
                                Enter your FS.com Order ID (e.g., FS12345678) to automatically import products and warranty information.
                            </p>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Order ID
                                </label>
                                <input
                                    type="text"
                                    value={orderId}
                                    onChange={(e) => setOrderId(e.target.value)}
                                    className="w-full px-3 py-2 border border-input rounded-md shadow-sm bg-background text-foreground"
                                    placeholder="FS..."
                                    required
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading || !orderId.trim()}
                                    className="btn-primary"
                                >
                                    {loading ? 'Importing...' : 'Import Order'}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                                Upload an FS.com Invoice PDF (e.g. 2024_invoice.pdf) to parse products and create assets.
                            </p>

                            <div className="border-2 border-dashed border-border-color rounded-lg p-6 text-center">
                                <input
                                    type="file"
                                    accept=".pdf"
                                    onChange={handleFileChange}
                                    className="hidden"
                                    id="invoice-upload"
                                />
                                <label htmlFor="invoice-upload" className="cursor-pointer block">
                                    <svg className="mx-auto h-12 w-12 text-muted-foreground mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <span className="text-primary font-medium hover:underline">Click to upload PDF</span>
                                    <p className="text-sm text-muted-foreground mt-1">
                                        {file ? file.name : 'No file selected'}
                                    </p>
                                </label>
                            </div>

                            {previewData && (
                                <div className="bg-subtle-card rounded-lg p-4 text-sm">
                                    <div className="grid grid-cols-2 gap-2 mb-3">
                                        <div>Order: <span className="font-medium">{previewData.order_number}</span></div>
                                        <div>Invoice: <span className="font-medium">{previewData.invoice_number}</span></div>
                                    </div>
                                    <div className="max-h-48 overflow-y-auto">
                                        <table className="w-full text-left">
                                            <thead>
                                                <tr className="border-b border-border-color">
                                                    <th className="pb-2">Part #</th>
                                                    <th className="pb-2">Qty</th>
                                                    <th className="pb-2">Price</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {previewData.products.map((p: any, i: number) => (
                                                    <tr key={i} className="border-b border-border-color/50">
                                                        <td className="py-2">{p.part_number || p.product_id}</td>
                                                        <td className="py-2">{p.quantity}</td>
                                                        <td className="py-2">${p.unit_price}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                    <div className="mt-2 text-right font-medium text-emerald-600">
                                        Total: ${previewData.products.reduce((acc: number, p: any) => acc + (p.total_price || (p.unit_price * p.quantity)), 0).toFixed(2)}
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-end gap-3 mt-4">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                {file && !previewData && (
                                    <button
                                        onClick={handlePreviewInvoice}
                                        disabled={loading}
                                        className="btn-primary bg-indigo-600 hover:bg-indigo-700"
                                    >
                                        {loading ? 'Parsing...' : 'Preview Invoice'}
                                    </button>
                                )}
                                {previewData && (
                                    <button
                                        onClick={handleImportInvoice}
                                        disabled={loading}
                                        className="btn-primary bg-green-600 hover:bg-green-700"
                                    >
                                        {loading ? 'Creating Assets...' : 'Import & Create Assets'}
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FSOrderImportModal;
