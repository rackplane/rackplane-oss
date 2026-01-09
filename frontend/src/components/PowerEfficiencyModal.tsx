// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Power Efficiency Advisor Modal
 * 
 * AI-powered analysis of devices in storage ranked by power-per-performance efficiency.
 * Helps operators choose optimal equipment for deployment.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import { formatAssetType } from '../utils/formatAssetType';

interface EfficiencyRanking {
    asset_id: number;
    asset_tag: string;
    manufacturer: string | null;
    model: string | null;
    asset_type: string;
    power_watts: number;
    performance_score: number;
    efficiency_score: number;
    efficiency_rating: string;
    specifications: Record<string, any>;
}

interface EfficiencySummary {
    total_analyzed: number;
    average_efficiency: number;
    best_efficiency: number;
    worst_efficiency: number;
}

interface EfficiencyReport {
    rankings: EfficiencyRanking[];
    summary: EfficiencySummary;
    explanation: string | null;
}

interface PowerEfficiencyModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelectAsset?: (assetId: number) => void;
}

const PowerEfficiencyModal: React.FC<PowerEfficiencyModalProps> = ({ isOpen, onClose, onSelectAsset }) => {
    const { t } = useWhiteLabel();
    const [report, setReport] = useState<EfficiencyReport | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [assetType, setAssetType] = useState<string>('server');
    const [includeExplanation, setIncludeExplanation] = useState(false);
    const [limit, setLimit] = useState(20);

    useEffect(() => {
        if (isOpen) {
            fetchEfficiencyReport();
        }
    }, [isOpen, assetType, limit]);

    const fetchEfficiencyReport = async () => {
        setLoading(true);
        setError(null);

        try {
            const headers = { Authorization: `Bearer ${localStorage.getItem('auth_token')}` };
            const params: Record<string, any> = {
                limit,
                include_explanation: includeExplanation
            };

            if (assetType && assetType !== 'all') {
                params.asset_type = assetType;
            }

            const response = await axios.get(`${API_URL}/api/v1/ai/power-efficiency`, {
                params,
                headers
            });

            setReport(response.data);
        } catch (err: any) {
            logger.error('Error fetching power efficiency report:', err);
            if (err.response?.status === 403) {
                setError('AI explanations require Pro or MSP subscription.');
            } else {
                setError(err.response?.data?.detail || 'Failed to analyze power efficiency.');
            }
        } finally {
            setLoading(false);
        }
    };

    const getRatingBadge = (rating: string) => {
        const colors: Record<string, string> = {
            excellent: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
            good: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
            fair: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
            poor: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
        };
        return colors[rating] || 'bg-gray-100 text-gray-800';
    };

    const handleExportCSV = () => {
        if (!report || report.rankings.length === 0) return;

        const headers = ['Rank', `${t('item')} Tag`, 'Manufacturer', 'Model', 'Type', 'Power (W)', 'Performance', 'Efficiency', 'Rating'];
        const rows = report.rankings.map((r, idx) => [
            idx + 1,
            r.asset_tag,
            r.manufacturer || '',
            r.model || '',
            r.asset_type,
            r.power_watts,
            r.performance_score.toFixed(1),
            r.efficiency_score.toFixed(3),
            r.efficiency_rating
        ]);

        const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `power_efficiency_report_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-xl font-bold text-primary flex items-center gap-2">
                            <span>⚡</span>
                            Power Efficiency Advisor
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Analyze {t('items').toLowerCase()} in {t('storage').toLowerCase()} by performance-per-watt efficiency
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Filters */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                    <div className="flex gap-4 items-center">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{t('item')} Type</label>
                            <select
                                value={assetType}
                                onChange={(e) => setAssetType(e.target.value)}
                                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                            >
                                <option value="all">All Types</option>
                                <option value="server">Servers</option>
                                <option value="network_switch">Switches</option>
                                <option value="gpu">GPUs</option>
                                <option value="storage">Storage</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Results</label>
                            <select
                                value={limit}
                                onChange={(e) => setLimit(Number(e.target.value))}
                                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                            >
                                <option value={10}>Top 10</option>
                                <option value={20}>Top 20</option>
                                <option value={50}>Top 50</option>
                            </select>
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                            <input
                                type="checkbox"
                                id="includeExplanation"
                                checked={includeExplanation}
                                onChange={(e) => setIncludeExplanation(e.target.checked)}
                                className="rounded border-gray-300 dark:border-gray-600"
                            />
                            <label htmlFor="includeExplanation" className="text-sm text-gray-700 dark:text-gray-300">
                                Include AI Explanation <span className="text-xs text-purple-600 dark:text-purple-400">(Pro)</span>
                            </label>
                        </div>
                        <button
                            onClick={fetchEfficiencyReport}
                            disabled={loading}
                            className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
                        >
                            {loading ? '🔄 Analyzing...' : '🔍 Analyze'}
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 flex-1 overflow-hidden flex flex-col">
                    {error && (
                        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200 rounded text-sm">
                            {error}
                        </div>
                    )}

                    {/* Summary Cards */}
                    {report && report.summary.total_analyzed > 0 && (
                        <div className="grid grid-cols-4 gap-4 mb-4">
                            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                                <div className="text-2xl font-bold text-gray-900 dark:text-white">{report.summary.total_analyzed}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">{t('items')} Analyzed</div>
                            </div>
                            <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4">
                                <div className="text-2xl font-bold text-green-700 dark:text-green-300">{report.summary.best_efficiency.toFixed(2)}</div>
                                <div className="text-xs text-green-600 dark:text-green-400">Best Efficiency</div>
                            </div>
                            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
                                <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">{report.summary.average_efficiency.toFixed(2)}</div>
                                <div className="text-xs text-blue-600 dark:text-blue-400">Average Efficiency</div>
                            </div>
                            <div className="bg-red-50 dark:bg-red-900/30 rounded-lg p-4">
                                <div className="text-2xl font-bold text-red-700 dark:text-red-300">{report.summary.worst_efficiency.toFixed(2)}</div>
                                <div className="text-xs text-red-600 dark:text-red-400">Worst Efficiency</div>
                            </div>
                        </div>
                    )}

                    {/* AI Explanation */}
                    {report?.explanation && (
                        <div className="mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                            <div className="flex items-center gap-2 mb-2">
                                <span>🤖</span>
                                <span className="text-sm font-semibold text-purple-700 dark:text-purple-300">AI Analysis</span>
                            </div>
                            <p className="text-sm text-purple-800 dark:text-purple-200">{report.explanation}</p>
                        </div>
                    )}

                    {/* Results Table */}
                    <div className="flex-1 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                                <tr>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 w-12">#</th>
                                    <th className="p-3 text-sm font-semibold text-gray-900 dark:text-gray-100">{t('item')}</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Type</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 text-right">Power (W)</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 text-right">Performance</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 text-right">Efficiency</th>
                                    <th className="p-3 text-sm font-semibold text-gray-700 dark:text-gray-300 text-center">Rating</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                {loading ? (
                                    <tr>
                                        <td colSpan={7} className="p-8 text-center text-gray-500">
                                            <div className="animate-pulse">Analyzing power efficiency...</div>
                                        </td>
                                    </tr>
                                ) : !report || report.rankings.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="p-8 text-center text-gray-500">
                                            No {t('items').toLowerCase()} in {t('storage').toLowerCase()} with power data found.
                                        </td>
                                    </tr>
                                ) : (
                                    report.rankings.map((ranking, idx) => (
                                        <tr
                                            key={ranking.asset_id}
                                            className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
                                            onClick={() => onSelectAsset?.(ranking.asset_id)}
                                        >
                                            <td className="p-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                                                {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : idx + 1}
                                            </td>
                                            <td className="p-3">
                                                <div className="font-medium text-gray-900 dark:text-gray-100">{ranking.asset_tag}</div>
                                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                                    {ranking.manufacturer} {ranking.model}
                                                </div>
                                            </td>
                                            <td className="p-3 text-sm text-gray-600 dark:text-gray-400">
                                                {formatAssetType(ranking.asset_type)}
                                            </td>
                                            <td className="p-3 text-sm text-gray-600 dark:text-gray-400 text-right font-mono">
                                                {ranking.power_watts}
                                            </td>
                                            <td className="p-3 text-sm text-gray-600 dark:text-gray-400 text-right font-mono">
                                                {ranking.performance_score.toFixed(1)}
                                            </td>
                                            <td className="p-3 text-sm text-gray-900 dark:text-gray-100 text-right font-bold font-mono">
                                                {ranking.efficiency_score.toFixed(3)}
                                            </td>
                                            <td className="p-3 text-center">
                                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRatingBadge(ranking.efficiency_rating)}`}>
                                                    {ranking.efficiency_rating}
                                                </span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                        Efficiency = Performance ÷ Power (higher is better)
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleExportCSV}
                            disabled={!report || report.rankings.length === 0}
                            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
                        >
                            📥 Export CSV
                        </button>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm font-medium"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PowerEfficiencyModal;
