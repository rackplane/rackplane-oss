import React from 'react';
import { useCapabilities } from '../contexts/CapabilityContext';

interface FeatureGateProps {
    feature: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
    /**
     * Controls what is rendered while capabilities are still loading.
     * - 'none': render nothing (may cause layout shifts)
     * - 'fallback': render the fallback content
     * - 'children': render children optimistically
     * - 'spinner': render a loading indicator
     *
     * Default: 'fallback'
     */
    loadingBehavior?: 'none' | 'fallback' | 'children' | 'spinner';
}

/**
 * Conditional rendering component based on feature availability.
 * 
 * Usage:
 * <FeatureGate feature="scan_assets" fallback={<UpgradePrompt />}>
 *   <ScannerComponent />
 * </FeatureGate>
 */
export const FeatureGate: React.FC<FeatureGateProps> = ({
    feature,
    children,
    fallback = null,
    loadingBehavior = 'fallback'
}) => {
    const { checkCapability, isLoading } = useCapabilities();

    if (isLoading) {
        switch (loadingBehavior) {
            case 'fallback':
                return <>{fallback}</>;
            case 'children':
                return <>{children}</>;
            case 'spinner':
                return (
                    <div className="flex justify-center p-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                    </div>
                );
            case 'none':
            default:
                return null;
        }
    }

    if (checkCapability(feature)) {
        return <>{children}</>;
    }

    return <>{fallback}</>;
};
