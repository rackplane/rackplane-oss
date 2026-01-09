// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import logger from '../utils/logger';

interface PricingTier {
    id: string;
    name: string;
    tagline?: string;
    price: number | null;
    price_id: string | null;
    features: string[];
    popular?: boolean;
    cta?: string;
    note?: string;
}

interface PricingResponse {
    tiers: PricingTier[];
    overage?: {
        ocr_scan: number;
        description: string;
    };
    concierge?: {
        price: number;
        description: string;
    };
}

interface SubscriptionStatus {
    tenant_id: number;
    tenant_name: string;
    subscription_tier: string;
    subscription_status: string;
    stripe_customer_id: string | null;
    rackplane_api_key_configured: boolean;
    features: Record<string, boolean>;
}

const Subscription: React.FC = () => {
    const { isAuthenticated } = useAuth();
    const [status, setStatus] = useState<SubscriptionStatus | null>(null);
    const [pricing, setPricing] = useState<PricingResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [upgrading, setUpgrading] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
    const [pendingApiKey, setPendingApiKey] = useState<string>('');
    const [activating, setActivating] = useState(false);
    const [activationSuccess, setActivationSuccess] = useState(false);

    // Check for API key in URL on mount
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const apiKeyFromUrl = params.get('api_key');
        if (apiKeyFromUrl && apiKeyFromUrl.startsWith('rk_')) {
            setPendingApiKey(apiKeyFromUrl);
        }
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            fetchSubscriptionData();
        }
    }, [isAuthenticated]);

    const fetchSubscriptionData = async (forceSync = false) => {
        try {
            setLoading(true);

            // Check for URL params to see if we need to force a sync (post-checkout)
            const params = new URLSearchParams(window.location.search);
            const shouldForceSync = forceSync || params.get('force_sync') === 'true';
            const apiKeyFromUrl = params.get('api_key');

            // If we have an API key in the URL (from checkout success page), activate it first
            if (apiKeyFromUrl && apiKeyFromUrl.startsWith('rk_')) {
                try {
                    logger.info('Auto-activating API key from checkout...');
                    await axios.post(`${API_URL}/api/v1/license/activate`, {
                        license_key: apiKeyFromUrl
                    });
                    logger.info('API key activated successfully');
                    // Clear the API key from URL for security
                    window.history.replaceState({}, '', window.location.pathname + '?success=true');
                } catch (activateErr) {
                    logger.error('Failed to auto-activate API key:', activateErr);
                    // Continue anyway - they can manually enter it in Settings
                }
            }

            // Try to get license status first, fallback to Stripe if needed
            try {
                const licenseRes = await axios.get(`${API_URL}/api/v1/license/status`);
                // Map license status to subscription status format
                setStatus({
                    tenant_id: 0,
                    tenant_name: '',
                    subscription_tier: licenseRes.data.tier || 'community',
                    subscription_status: licenseRes.data.license_warning ? 'warning' : 'active',
                    stripe_customer_id: null,
                    rackplane_api_key_configured: true,
                    features: licenseRes.data.features || {}
                });

                // If we successfully synced and got the expected tier confirm success
                const expectedTier = params.get('tier');
                if (shouldForceSync && expectedTier && licenseRes.data.tier === expectedTier) {
                    // Clear URL params to clean up
                    window.history.replaceState({}, '', window.location.pathname);
                }

            } catch (licenseErr) {
                // Fallback to Stripe status if license endpoint fails
                try {
                    const statusRes = await axios.get(`${API_URL}/api/v1/stripe/status`, {
                        params: { sync_remote: shouldForceSync }
                    });
                    setStatus(statusRes.data);
                } catch (stripeErr) {
                    logger.error('Error fetching subscription:', stripeErr);
                }
            }

            // Try to get pricing from Stripe (for display purposes)
            try {
                const pricingRes = await axios.get(`${API_URL}/api/v1/stripe/pricing`);
                setPricing(pricingRes.data);
            } catch (pricingErr) {
                // If Stripe pricing fails, create default pricing structure
                setPricing({
                    tiers: [
                        { id: 'community', name: 'Community', price: null, price_id: null, features: ['Basic asset management', 'Built-in OCR', '1 user', '1 tenant'], cta: 'Free Forever' },
                        { id: 'starter', name: 'Starter', price: null, price_id: null, features: ['Everything in Community', '100 Cloud OCR scans/month', 'Warranty lookup', 'Label printing'], cta: 'Enter License Key' },
                        { id: 'pro', name: 'Pro', price: null, price_id: null, features: ['Everything in Starter', 'Unlimited users', '500 Cloud OCR scans/month', 'API access', 'NetBox sync'], popular: true, cta: 'Enter License Key' },
                        { id: 'msp', name: 'MSP', price: null, price_id: null, features: ['Everything in Pro', 'Multi-tenant management', 'Admin portal', 'Unlimited Cloud OCR'], cta: 'Enter License Key' }
                    ]
                });
            }
            setError(null);
        } catch (err: any) {
            logger.error('Error fetching subscription:', err);
            setError('Failed to load subscription information');
        } finally {
            setLoading(false);
        }
    };

    const handleUpgrade = async (tier: PricingTier) => {
        // If tier has a Stripe price_id, use Stripe checkout
        if (tier.price_id && tier.price !== null) {
            setUpgrading(tier.id);
            try {
                const response = await axios.post(`${API_URL}/api/v1/stripe/create-checkout-session`, {
                    price_id: tier.price_id
                });
                // Redirect to Stripe checkout
                window.location.href = response.data.checkout_url;
            } catch (err: any) {
                logger.error('Error creating checkout session:', err);
                const errorMessage = err.response?.data?.detail || err.message || 'Failed to start checkout';
                setError(errorMessage);
            } finally {
                setUpgrading(null);
            }
        } else {
            // No Stripe price - MSP tier, contact sales
            window.location.href = 'mailto:sales@rackplane.com?subject=MSP%20Tier%20Inquiry';
        }
    };

    const handleManageBilling = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/v1/stripe/customer-portal`);
            window.location.href = response.data.portal_url;
        } catch (err: any) {
            logger.error('Error opening portal:', err);
            setError(err.response?.data?.detail || 'Failed to open billing portal');
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="text-center py-12">Loading subscription information...</div>
            </div>
        );
    }

    const currentTier = status?.subscription_tier?.toLowerCase() || 'free';

    return (
        <div className="container mx-auto px-4 py-8 max-w-6xl">
            {/* Header */}
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-foreground mb-2">Subscription Plans</h1>
                <p className="text-muted-foreground">Choose the plan that's right for your team.</p>
                <p className="text-sm text-muted-foreground mt-2">Upgrade via Stripe or activate a license key.</p>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 text-center">
                    {error}
                </div>
            )}

            {/* API Key Activation Section - shown when key is in URL */}
            {pendingApiKey && !activationSuccess && (
                <div className="bg-green-50 dark:bg-green-900/30 border-2 border-green-500 rounded-lg p-6 mb-8">
                    <div className="text-center mb-4">
                        <span className="text-4xl">🎉</span>
                        <h2 className="text-xl font-bold text-green-600 dark:text-green-400 mt-2">Payment Successful!</h2>
                        <p className="text-gray-700 dark:text-gray-300 mt-2">Your API key is ready to activate. Click the button below to complete your upgrade.</p>
                    </div>
                    <div className="max-w-md mx-auto">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Your API Key:</label>
                        <input
                            type="text"
                            value={pendingApiKey}
                            onChange={(e) => setPendingApiKey(e.target.value)}
                            className="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white font-mono text-sm mb-4"
                            readOnly
                        />
                        <button
                            onClick={async () => {
                                setActivating(true);
                                setError(null);
                                try {
                                    await axios.post(`${API_URL}/api/v1/license/activate`, {
                                        license_key: pendingApiKey
                                    });
                                    setActivationSuccess(true);
                                    setPendingApiKey('');
                                    // Clear URL params
                                    window.history.replaceState({}, '', window.location.pathname);
                                    // Refresh subscription data
                                    fetchSubscriptionData();
                                } catch (err: any) {
                                    setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to activate. Try pasting the key in Settings.');
                                } finally {
                                    setActivating(false);
                                }
                            }}
                            disabled={activating}
                            className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg transition disabled:opacity-50"
                        >
                            {activating ? 'Activating...' : '✓ Activate My Subscription'}
                        </button>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 text-center">
                            Or copy the key and paste it in <a href="/settings" className="text-blue-600 dark:text-blue-400 hover:underline">Settings → License & Subscription</a>
                        </p>
                    </div>
                </div>
            )}

            {activationSuccess && (
                <div className="bg-green-50 dark:bg-green-900/30 border-2 border-green-500 rounded-lg p-6 mb-8 text-center">
                    <span className="text-4xl">✅</span>
                    <h2 className="text-xl font-bold text-green-600 dark:text-green-400 mt-2">Subscription Activated!</h2>
                    <p className="text-gray-700 dark:text-gray-300 mt-2">Your account has been upgraded. Enjoy your new features!</p>
                </div>
            )}


            {/* Pricing Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                {pricing?.tiers.map((tier) => {
                    const isCurrent = currentTier === tier.id.toLowerCase();
                    const displayPrice = tier.price !== null
                        ? (billingCycle === 'annual' ? Math.round(tier.price * 0.8) : tier.price)
                        : null;

                    return (
                        <div
                            key={tier.id}
                            className={`bg-card rounded-xl shadow-lg p-6 relative ${tier.popular ? 'ring-2 ring-primary' : 'border border-border'
                                } ${isCurrent ? 'ring-2 ring-green-500' : ''}`}
                        >
                            {/* Popular Badge */}
                            {tier.popular && (
                                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                                    <span className="bg-primary text-white text-xs font-bold px-3 py-1 rounded-full">
                                        POPULAR
                                    </span>
                                </div>
                            )}

                            {/* Current Badge */}
                            {isCurrent && (
                                <div className="absolute -top-3 right-4">
                                    <span className="bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                                        CURRENT
                                    </span>
                                </div>
                            )}

                            <div className="text-center mb-6 pt-2">
                                <h3 className="text-xl font-bold text-foreground">{tier.name}</h3>
                                {tier.tagline && (
                                    <p className="text-sm text-muted-foreground">{tier.tagline}</p>
                                )}
                                <div className="mt-4">
                                    {tier.price !== null ? (
                                        <>
                                            <span className="text-4xl font-bold text-foreground">${displayPrice}</span>
                                            <span className="text-muted-foreground">/month</span>
                                        </>
                                    ) : (
                                        <span className="text-2xl font-bold text-foreground">License Required</span>
                                    )}
                                </div>
                                {tier.note && (
                                    <p className="text-xs text-muted-foreground mt-2">{tier.note}</p>
                                )}
                            </div>

                            <ul className="space-y-3 mb-6">
                                {tier.features.map((feature, idx) => (
                                    <li key={idx} className="flex items-start text-sm">
                                        {feature.includes('Everything in') ? (
                                            <span className="text-muted-foreground">{feature}</span>
                                        ) : (
                                            <>
                                                <span className="text-green-500 mr-2 flex-shrink-0">✓</span>
                                                <span className="text-foreground">{feature}</span>
                                            </>
                                        )}
                                    </li>
                                ))}
                            </ul>

                            <button
                                onClick={() => handleUpgrade(tier)}
                                disabled={isCurrent || upgrading === tier.id}
                                className={`w-full py-3 rounded-lg font-semibold transition ${isCurrent
                                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                    : tier.id === 'msp'
                                        ? 'bg-gray-600 text-white hover:bg-gray-700'
                                        : tier.popular
                                            ? 'bg-primary text-white hover:bg-primary/90'
                                            : 'bg-blue-600 text-white hover:bg-blue-700'
                                    } disabled:opacity-50`}
                            >
                                {isCurrent
                                    ? 'Current Plan'
                                    : upgrading === tier.id
                                        ? 'Redirecting...'
                                        : tier.price_id && tier.price !== null
                                            ? `Subscribe - $${tier.price}/mo`
                                            : tier.cta || 'Contact Sales'}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Overage Info */}
            {pricing?.overage && (
                <div className="text-center text-sm text-muted-foreground mb-8">
                    {pricing.overage.description}
                </div>
            )}

            {/* Have a license? */}
            <div className="text-center mt-8 text-sm text-muted-foreground">
                Have a license key? <a href="/settings" className="text-primary underline">Activate it in Settings</a>
            </div>
        </div>
    );
};

export default Subscription;
