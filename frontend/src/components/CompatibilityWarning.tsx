// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * CompatibilityWarning Component
 * Displays cable/port compatibility warnings in different styles
 * based on the compatibility level returned from the API.
 */

import React from 'react';

export interface CompatibilityResult {
    compatible: boolean;
    level: 'perfect' | 'compatible' | 'downgrade' | 'depends_on_transceiver' | 'incompatible' | 'unknown';
    message: string;
    allow_connection: boolean;
}

interface CompatibilityWarningProps {
    result: CompatibilityResult;
    onDismiss?: () => void;
}

const CompatibilityWarning: React.FC<CompatibilityWarningProps> = ({ result, onDismiss }) => {
    // Perfect match - show success briefly
    if (result.level === 'perfect') {
        return (
            <div className="flex items-center p-3 bg-green-50 border border-green-200 rounded-lg text-green-800">
                <span className="text-xl mr-2">✓</span>
                <span className="text-sm">{result.message}</span>
                {onDismiss && (
                    <button onClick={onDismiss} className="ml-auto text-green-600 hover:text-green-800">
                        ×
                    </button>
                )}
            </div>
        );
    }

    // Compatible or depends on transceiver - show info
    if (result.level === 'compatible' || result.level === 'depends_on_transceiver') {
        return (
            <div className="flex items-center p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800">
                <span className="text-xl mr-2">ℹ️</span>
                <span className="text-sm">{result.message}</span>
                {onDismiss && (
                    <button onClick={onDismiss} className="ml-auto text-blue-600 hover:text-blue-800">
                        ×
                    </button>
                )}
            </div>
        );
    }

    // Downgrade - show warning
    if (result.level === 'downgrade') {
        return (
            <div className="flex items-start p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-yellow-800">
                <span className="text-xl mr-2">⚠️</span>
                <div className="flex-1">
                    <span className="font-semibold text-sm">Performance Warning</span>
                    <p className="text-sm mt-1">{result.message}</p>
                </div>
                {onDismiss && (
                    <button onClick={onDismiss} className="ml-2 text-yellow-600 hover:text-yellow-800">
                        ×
                    </button>
                )}
            </div>
        );
    }

    // Incompatible - show error
    if (result.level === 'incompatible') {
        return (
            <div className="flex items-start p-3 bg-red-50 border border-red-300 rounded-lg text-red-800">
                <span className="text-xl mr-2">⚠️</span>
                <div className="flex-1">
                    <span className="font-semibold text-sm">Compatibility Warning</span>
                    <p className="text-sm mt-1">{result.message}</p>
                    <p className="text-xs text-red-600 mt-1 italic">
                        Connection was created, but may not function correctly.
                    </p>
                </div>
                {onDismiss && (
                    <button onClick={onDismiss} className="ml-2 text-red-600 hover:text-red-800">
                        ×
                    </button>
                )}
            </div>
        );
    }

    // Unknown - show info with question
    if (result.level === 'unknown') {
        return (
            <div className="flex items-center p-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
                <span className="text-xl mr-2">❓</span>
                <span className="text-sm">{result.message}</span>
                {onDismiss && (
                    <button onClick={onDismiss} className="ml-auto text-gray-500 hover:text-gray-700">
                        ×
                    </button>
                )}
            </div>
        );
    }

    return null;
};

export default CompatibilityWarning;
