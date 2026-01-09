// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * SourceBadge Component
 * 
 * Displays visual indicators for SKU data source:
 * - Local (green): From user's own catalog
 * - Cached (blue): Previously fetched, stored locally
 * - Remote (purple): Fresh from Global Catalog
 * - Offline/Generic (yellow): Manual entry required
 */

import React from 'react';

interface SourceBadgeProps {
    source: 'local' | 'cache' | 'remote' | 'offline';
    is_generic?: boolean;
    className?: string;
}

const SourceBadge: React.FC<SourceBadgeProps> = ({ source, is_generic = false, className = '' }) => {
    if (is_generic) {
        return (
            <span className={`px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full inline-flex items-center ${className}`}>
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Info Not Found
            </span>
        );
    }

    const badges: Record<string, { bg: string; text: string; icon: string; label: string }> = {
        local: {
            bg: 'bg-green-100',
            text: 'text-green-800',
            icon: '✓',
            label: 'Local',
        },
        cache: {
            bg: 'bg-blue-100',
            text: 'text-blue-800',
            icon: '📦',
            label: 'Cached',
        },
        remote: {
            bg: 'bg-purple-100',
            text: 'text-purple-800',
            icon: '☁️',
            label: 'Global',
        },
        offline: {
            bg: 'bg-yellow-100',
            text: 'text-yellow-800',
            icon: '⚠️',
            label: 'Offline',
        },
    };

    const badge = badges[source] || badges.offline;

    return (
        <span className={`px-2 py-1 ${badge.bg} ${badge.text} text-xs font-medium rounded-full ${className}`}>
            {badge.icon} {badge.label}
        </span>
    );
};

export default SourceBadge;
