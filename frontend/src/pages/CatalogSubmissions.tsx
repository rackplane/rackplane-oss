import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import {
    SUBMISSION_STATUS,
    getStatusBadgeClass
} from '../constants/submissionStatus';
import { FeatureGate } from '../components/FeatureGate';
import { UpgradePrompt } from '../components/UpgradePrompt';

interface Submission {
    id: number;
    vendor: string;
    sku: string;
    data_snapshot: Record<string, any>;
    source_url?: string;
    submission_method: string;
    status: string;
    submitted_by_user_id: number;
    submitted_at: string;
    reviewed_by_user_id?: number;
    reviewed_at?: string;
    review_notes?: string;
}

interface ExistingCatalogSku {
    id: number;
    vendor: string;
    sku: string;
    name: string;
    manufacturer?: string;
    part_number?: string;
    asset_type?: string;
    price_usd?: number;
}

const CatalogSubmissions: React.FC = () => {
    const { isSuperAdmin } = useAuth();
    const [submissions, setSubmissions] = useState<Submission[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState('');
    const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
    const [existingData, setExistingData] = useState<ExistingCatalogSku | null>(null);
    const [reviewNotes, setReviewNotes] = useState('');
    const [processing, setProcessing] = useState(false);
    const [resyncingId, setResyncingId] = useState<number | null>(null);

    const loadSubmissions = React.useCallback(async (signal?: AbortSignal) => {
        setLoading(true);
        try {
            const endpoint = statusFilter === 'pending' ? '/catalog-submissions/pending' : `/catalog-submissions/?status=${statusFilter}`;
            // @ts-ignore - signal mismatch with axios version potentially, but standard in newer ones. Casting to any to be safe or just passing config.
            const response = await axios.get(`${API_URL}/api/v1${endpoint}`, { signal });
            if (!signal?.aborted) {
                setSubmissions(response.data);
            }
        } catch (err: unknown) {
            if (axios.isCancel(err)) {
                return;
            }
            if (!signal?.aborted) {
                if (axios.isAxiosError(err)) {
                    setError(err.response?.data?.detail || 'Failed to load submissions');
                } else {
                    setError('Failed to load submissions: Unknown error');
                }
            }
        } finally {
            if (!signal?.aborted) {
                setLoading(false);
            }
        }
    }, [statusFilter]);

    useEffect(() => {
        const controller = new AbortController();
        loadSubmissions(controller.signal);
        return () => controller.abort();
    }, [loadSubmissions]);

    const handleViewDetails = async (submission: Submission) => {
        setSelectedSubmission(submission);
        setReviewNotes('');

        // Try to fetch existing catalog data for comparison
        try {
            const response = await axios.get(`${API_URL}/api/v1/global-catalog/lookup?vendor=${submission.vendor}&sku=${submission.sku}`);
            setExistingData(response.data);
        } catch {
            setExistingData(null);
        }
    };

    const handleApprove = async () => {
        if (!selectedSubmission) return;
        setProcessing(true);
        try {
            await axios.put(`${API_URL}/api/v1/catalog-submissions/${selectedSubmission.id}/approve`, {
                notes: reviewNotes || null,
            });
            setSelectedSubmission(null);
            loadSubmissions();
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || 'Failed to approve');
            } else {
                setError('Failed to approve: Unknown error');
            }
        } finally {
            setProcessing(false);
        }
    };

    const handleReject = async () => {
        if (!selectedSubmission) return;
        if (!reviewNotes.trim()) {
            setError('Please provide rejection notes');
            return;
        }
        setProcessing(true);
        try {
            await axios.put(`${API_URL}/api/v1/catalog-submissions/${selectedSubmission.id}/reject`, {
                notes: reviewNotes,
            });
            setSelectedSubmission(null);
            loadSubmissions();
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || 'Failed to reject');
            } else {
                setError('Failed to reject: Unknown error');
            }
        } finally {
            setProcessing(false);
        }
    };

    const handleResync = async (submissionId: number) => {
        setResyncingId(submissionId);
        try {
            await axios.post(`${API_URL}/api/v1/catalog-submissions/${submissionId}/resync`);
            loadSubmissions();
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || 'Failed to resync');
            } else {
                setError('Failed to resync: Unknown error');
            }
        } finally {
            setResyncingId(null);
        }
    };

    const handleResyncAllFailed = async () => {
        setProcessing(true);
        try {
            await axios.post(`${API_URL}/api/v1/catalog-submissions/resync-all-failed`);
            loadSubmissions();
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || 'Failed to resync all');
            } else {
                setError('Failed to resync all: Unknown error');
            }
        } finally {
            setProcessing(false);
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    const getStatusBadge = (status: string) => getStatusBadgeClass(status);

    const getMethodBadge = (method: string) => {
        const badges: Record<string, string> = {
            browser_scrape: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
            manual_edit: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
            api_import: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
        };
        return badges[method] || 'bg-gray-100 text-gray-800';
    };

    return (
        <FeatureGate
            feature="global_catalog"
            fallback={
                <div className="p-6">
                    <h1 className="text-2xl font-bold text-primary mb-6">Catalog Submissions</h1>
                    <UpgradePrompt
                        feature="global_catalog"
                        showDetails={true}
                    />
                </div>
            }
        >
            <div className="p-6">
                <h1 className="text-2xl font-bold text-primary mb-6">Catalog Submissions</h1>

            {/* Filters */}
            <div className="flex gap-4 mb-6">
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="input"
                >
                    <option value="">All</option>
                    <option value={SUBMISSION_STATUS.PENDING}>Pending Review</option>
                    <option value={SUBMISSION_STATUS.TENANT_APPROVED}>Tenant Approved (Awaiting Final)</option>
                    <option value={SUBMISSION_STATUS.APPROVED}>Approved</option>
                    <option value={SUBMISSION_STATUS.REJECTED}>Rejected</option>
                </select>
                <button onClick={() => loadSubmissions()} className="btn btn-secondary">
                    Refresh
                </button>
                {isSuperAdmin && (
                    <button
                        onClick={handleResyncAllFailed}
                        disabled={processing}
                        className="btn bg-orange-100 text-orange-800 hover:bg-orange-200 border border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800 transition-colors"
                        title="Resync all approved submissions that failed synchronization"
                    >
                        {processing ? 'Processing...' : (
                            <>
                                <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Resync All Failed
                            </>
                        )}
                    </button>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
                    <p className="text-red-600 dark:text-red-400">{error}</p>
                    <button onClick={() => setError(null)} className="text-sm underline">Dismiss</button>
                </div>
            )}

            {/* Submissions Table */}
            <div className="card overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendor</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Method</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submitted</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {loading ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td>
                            </tr>
                        ) : submissions.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No submissions found</td>
                            </tr>
                        ) : (
                            submissions.map((sub) => (
                                <tr key={sub.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                                    <td className="px-4 py-3 text-primary">{sub.vendor}</td>
                                    <td className="px-4 py-3 text-primary font-mono text-sm">{sub.sku}</td>
                                    <td className="px-4 py-3 text-primary max-w-[200px] truncate" title={sub.data_snapshot?.name || 'No Name'}>
                                        {sub.data_snapshot?.name || 'No Name'}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 rounded text-xs ${getMethodBadge(sub.submission_method)}`}>
                                            {sub.submission_method.replace(/_/g, ' ')}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex flex-col gap-1">
                                            <span className={`px-2 py-1 rounded text-xs w-fit ${getStatusBadge(sub.status)}`}>
                                                {sub.status}
                                            </span>
                                            {sub.status === SUBMISSION_STATUS.APPROVED && sub.data_snapshot?.sync_info && (
                                                <>
                                                    {sub.data_snapshot.sync_info.status === 'success' ? (
                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold w-fit border ${String(sub.data_snapshot.sync_info.source_id || '').startsWith('submission:')
                                                            ? 'bg-blue-50 text-blue-600 border-blue-200'
                                                            : 'bg-green-50 text-green-600 border-green-200'
                                                            }`}>
                                                            {String(sub.data_snapshot.sync_info.source_id || '').startsWith('submission:')
                                                                ? 'GLOBAL PENDING'
                                                                : 'GLOBAL LIVE'}
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-0.5 rounded text-[10px] font-bold w-fit bg-red-50 text-red-600 border border-red-200">
                                                            SYNC FAILED
                                                        </span>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-500">{formatDate(sub.submitted_at)}</td>
                                    <td className="px-4 py-3">
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleViewDetails(sub)}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View
                                            </button>
                                            {isSuperAdmin && sub.status === SUBMISSION_STATUS.APPROVED &&
                                                sub.data_snapshot?.sync_info?.status !== 'success' && (
                                                    <button
                                                        onClick={() => handleResync(sub.id)}
                                                        disabled={resyncingId === sub.id}
                                                        className="text-orange-600 hover:text-orange-800 text-sm font-medium"
                                                    >
                                                        {resyncingId === sub.id ? '...' : (
                                                            <>
                                                                <svg className="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                                </svg>
                                                                Resync
                                                            </>
                                                        )}
                                                    </button>
                                                )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Detail Modal */}
            {selectedSubmission && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="p-6">
                            <div className="flex justify-between items-start mb-4">
                                <h2 className="text-xl font-bold text-primary">
                                    Review Submission: {selectedSubmission.vendor} / {selectedSubmission.sku}
                                </h2>
                                <button
                                    onClick={() => setSelectedSubmission(null)}
                                    className="text-gray-500 hover:text-gray-700 text-2xl"
                                >
                                    ×
                                </button>
                            </div>

                            {/* Source URL */}
                            {selectedSubmission.source_url && (
                                <p className="text-sm text-gray-500 mb-4">
                                    Source: <a href={selectedSubmission.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">{selectedSubmission.source_url}</a>
                                </p>
                            )}

                            {/* Sync Error */}
                            {/* Sync Status Info */}
                            {selectedSubmission.data_snapshot?.sync_info && (
                                <div className={`border rounded-lg p-4 mb-6 ${selectedSubmission.data_snapshot.sync_info.status === 'success'
                                    ? (String(selectedSubmission.data_snapshot.sync_info.source_id || '').startsWith('submission:')
                                        ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
                                        : 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800')
                                    : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                                    }`}>
                                    {selectedSubmission.data_snapshot.sync_info.status === 'failed' ? (
                                        <>
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-red-700 dark:text-red-400 font-semibold mb-1">
                                                    <span className="text-lg">
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                                        </svg>
                                                    </span> Catalog Sync Failed
                                                </div>
                                                {isSuperAdmin && (
                                                    <button
                                                        onClick={() => handleResync(selectedSubmission.id)}
                                                        disabled={resyncingId === selectedSubmission.id}
                                                        className="px-3 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded text-sm font-medium"
                                                    >
                                                        {resyncingId === selectedSubmission.id ? 'Resyncing...' : '🔄 Retry Sync'}
                                                    </button>
                                                )}
                                            </div>
                                            <p className="text-sm text-red-600 dark:text-red-400">
                                                {selectedSubmission.data_snapshot.sync_info.error || 'Unknown error occurred during central catalog synchronization.'}
                                            </p>
                                        </>
                                    ) : (
                                        <>
                                            {String(selectedSubmission.data_snapshot.sync_info.source_id || '').startsWith('submission:') ? (
                                                <>
                                                    <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-semibold mb-1">
                                                        <span className="text-lg">
                                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                                            </svg>
                                                        </span> Global Approval Pending
                                                    </div>
                                                    <p className="text-sm text-blue-600 dark:text-blue-400">
                                                        This item has been sent to the RackPlane Global Queue (ID: {selectedSubmission.data_snapshot.sync_info.source_id}) and is waiting for review by a super admin.
                                                    </p>
                                                </>
                                            ) : (
                                                <>
                                                    <div className="flex items-center gap-2 text-green-700 dark:text-green-400 font-semibold mb-1">
                                                        <span className="text-lg">
                                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0116 10c0 .34-.028.675-.083 1H15a2 2 0 00-2 2v2.197A5.973 5.973 0 0110 16v-2a2 2 0 00-2-2 2 2 0 01-2-2 2 2 0 00-1.668-1.973z" clipRule="evenodd" />
                                                            </svg>
                                                        </span> Global Catalog Live
                                                    </div>
                                                    <p className="text-sm text-green-600 dark:text-green-400">
                                                        This item has been successfully published to the Global Catalog.
                                                    </p>
                                                </>
                                            )}
                                            <p className="text-[10px] opacity-75 mt-2">
                                                Synced at: {new Date(selectedSubmission.data_snapshot.sync_info.synced_at || Date.now()).toLocaleString()}
                                            </p>
                                        </>
                                    )}
                                </div>
                            )}


                            {/* Diff View */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                                {/* Existing Data */}
                                <div>
                                    <h3 className="font-semibold text-primary mb-2">Current Catalog Data</h3>
                                    {existingData ? (
                                        <div className="bg-gray-100 dark:bg-gray-800 rounded p-4 space-y-2 text-sm">
                                            <p><strong>Name:</strong> {existingData.name}</p>
                                            <p><strong>Manufacturer:</strong> {existingData.manufacturer || '—'}</p>
                                            <p><strong>Part Number:</strong> {existingData.part_number || '—'}</p>
                                            <p><strong>Asset Type:</strong> {existingData.asset_type || '—'}</p>
                                            <p><strong>Price:</strong> {existingData.price_usd ? `$${existingData.price_usd}` : '—'}</p>
                                        </div>
                                    ) : (
                                        <div className="bg-gray-100 dark:bg-gray-800 rounded p-4 text-sm text-gray-500">
                                            Not in catalog (new entry)
                                        </div>
                                    )}
                                </div>

                                {/* Proposed Data */}
                                <div>
                                    <h3 className="font-semibold text-primary mb-2">Proposed Data</h3>
                                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-4 space-y-2 text-sm">
                                        <p><strong>Name:</strong> {selectedSubmission.data_snapshot?.name || '—'}</p>
                                        <p><strong>Manufacturer:</strong> {selectedSubmission.data_snapshot?.manufacturer || '—'}</p>
                                        <p><strong>Part Number:</strong> {selectedSubmission.data_snapshot.part_number || '—'}</p>
                                        <p><strong>Asset Type:</strong> {selectedSubmission.data_snapshot.asset_type || '—'}</p>
                                        <p><strong>Price:</strong> {selectedSubmission.data_snapshot.price_usd ? `$${selectedSubmission.data_snapshot.price_usd}` : '—'}</p>
                                        <p><strong>Description:</strong> {selectedSubmission.data_snapshot.description || '—'}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Specifications */}
                            {selectedSubmission.data_snapshot.specifications && Object.keys(selectedSubmission.data_snapshot.specifications).length > 0 && (
                                <div className="mb-6">
                                    <h3 className="font-semibold text-primary mb-2">Specifications</h3>
                                    <pre className="bg-gray-100 dark:bg-gray-800 rounded p-4 text-sm overflow-auto max-h-40">
                                        {JSON.stringify(selectedSubmission.data_snapshot.specifications, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Review Notes Input - show for actionable statuses */}
                            {(selectedSubmission.status === SUBMISSION_STATUS.PENDING ||
                                (selectedSubmission.status === SUBMISSION_STATUS.TENANT_APPROVED && isSuperAdmin)) && (
                                    <div className="mb-6">
                                        <label className="block text-sm font-medium text-primary mb-2">Review Notes</label>
                                        <textarea
                                            value={reviewNotes}
                                            onChange={(e) => setReviewNotes(e.target.value)}
                                            rows={3}
                                            className="input w-full"
                                            placeholder="Optional notes (required for rejection)"
                                        />
                                    </div>
                                )}

                            {/* Already Reviewed - show for non-actionable items */}
                            {selectedSubmission.status !== SUBMISSION_STATUS.PENDING &&
                                selectedSubmission.status !== SUBMISSION_STATUS.TENANT_APPROVED &&
                                selectedSubmission.review_notes && (
                                    <div className="mb-6">
                                        <h3 className="font-semibold text-primary mb-2">Review Notes</h3>
                                        <p className="text-gray-600 dark:text-gray-400">{selectedSubmission.review_notes}</p>
                                    </div>
                                )}

                            {/* Show previous notes for tenant_approved items */}
                            {selectedSubmission.status === SUBMISSION_STATUS.TENANT_APPROVED && selectedSubmission.review_notes && (
                                <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                                    <h3 className="font-semibold text-blue-800 dark:text-blue-300 mb-2">Tenant Admin Notes</h3>
                                    <p className="text-blue-700 dark:text-blue-400">{selectedSubmission.review_notes}</p>
                                </div>
                            )}

                            {/* Actions - show for pending (all admins) or tenant_approved (super admin only) */}
                            {(selectedSubmission.status === SUBMISSION_STATUS.PENDING ||
                                (selectedSubmission.status === SUBMISSION_STATUS.TENANT_APPROVED && isSuperAdmin)) && (
                                    <div className="flex gap-4">
                                        <button
                                            onClick={handleApprove}
                                            disabled={processing}
                                            className="btn bg-green-600 hover:bg-green-700 text-white"
                                        >
                                            {processing ? 'Processing...' : (isSuperAdmin && selectedSubmission.status === SUBMISSION_STATUS.TENANT_APPROVED ? '✓ Final Approve' : '✓ Approve')}
                                        </button>
                                        <button
                                            onClick={handleReject}
                                            disabled={processing}
                                            className="btn bg-red-600 hover:bg-red-700 text-white"
                                        >
                                            {processing ? 'Processing...' : '✗ Reject'}
                                        </button>
                                        <button
                                            onClick={() => setSelectedSubmission(null)}
                                            className="btn btn-secondary"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                )}
                        </div>
                    </div>
                </div>
            )
            }
        </div >
        </FeatureGate>
    );
};

export default CatalogSubmissions;
