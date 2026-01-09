import React from 'react';
import { useCapabilities } from '../contexts/CapabilityContext';
import { getPremiumFeatureMessage } from '../constants/featureMessages';

interface UpgradePromptProps {
    feature?: string;
    message?: string;
    showDetails?: boolean;
    className?: string;
}

// Static tier display names
const TIER_NAMES: Record<string, string> = {
    community: 'Community',
    starter: 'Starter',
    pro: 'Pro',
    msp: 'MSP'
};

// Consistent styling for the upgrade prompt container
const PROMPT_CONTAINER_CLASSES = "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4";

/**
 * Component that displays an upgrade prompt for premium features.
 *
 * Usage:
 * <UpgradePrompt feature="cloud_ocr" />
 * <UpgradePrompt message="This feature requires a Pro subscription" />
 */
export const UpgradePrompt: React.FC<UpgradePromptProps> = ({
    feature,
    message,
    showDetails = true,
    className = ''
}): JSX.Element => {
    const { capabilities } = useCapabilities();

    // Default to null until capabilities load to avoid showing incorrect messaging
    const buildMode = capabilities?.build_mode || null;
    const tier: string = capabilities?.tier || 'community';
    const displayTier = TIER_NAMES[tier as keyof typeof TIER_NAMES] || tier;

    // Determine display message with standardized messaging
    let displayMessage = message;

    if (!displayMessage) {
        if (buildMode === null) {
            // Capabilities not yet loaded
            displayMessage = 'Checking feature availability...';
        } else if (feature) {
            // Use standardized feature-specific message
            displayMessage = getPremiumFeatureMessage(feature);
        } else if (buildMode === 'oss') {
            displayMessage = 'This feature requires RackPlane Premium.';
        } else {
            displayMessage = 'This feature is not available in your current plan.';
        }
    }

    return (
        <div className={`${PROMPT_CONTAINER_CLASSES} ${className}`}>
            <div className="flex items-start">
                <div className="flex-shrink-0">
                    <svg
                        className="h-5 w-5 text-blue-400"
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        aria-hidden="true"
                        focusable="false"
                    >
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                </div>
                <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                        {displayMessage}
                    </h3>
                    {showDetails && (
                        <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                            {buildMode === 'oss' && (
                                <p className="mb-2">
                                    You are currently using <strong>RackPlane OSS</strong>.
                                    Upgrade to RackPlane Premium to access advanced features like Cloud OCR,
                                    global catalog, and vendor integrations.
                                </p>
                            )}
                            {buildMode === 'premium' && (
                                <p className="mb-2">
                                    Current plan: <strong>{displayTier}</strong>
                                </p>
                            )}
                            <a
                                href="/subscription"
                                className="font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 underline"
                            >
                                View pricing and upgrade options →
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default UpgradePrompt;
