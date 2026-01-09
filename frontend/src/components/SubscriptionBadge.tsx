// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Subscription Badge Component - Shows current tier on every page

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';

interface SubscriptionBadgeProps {
    className?: string;
}

const SubscriptionBadge: React.FC<SubscriptionBadgeProps> = ({ className = '' }) => {
    const [tier, setTier] = useState<string>('community');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTier = async () => {
            try {
                // Try license status first (most accurate)
                const response = await axios.get(`${API_URL}/api/v1/license/status`);
                setTier(response.data.tier || 'community');
            } catch (err) {
                // Fallback to stripe status
                try {
                    const stripeRes = await axios.get(`${API_URL}/api/v1/stripe/status`);
                    setTier(stripeRes.data.subscription_tier || 'community');
                } catch {
                    setTier('community');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchTier();
    }, []);

    // Tier display names and colors
    const getTierInfo = (tierName: string) => {
        const tierLower = tierName?.toLowerCase() || 'community';
        switch (tierLower) {
            case 'msp':
                return { name: 'MSP', color: 'bg-purple-600', icon: '🏢' };
            case 'pro':
                return { name: 'Pro', color: 'bg-green-600', icon: '⭐' };
            case 'starter':
                return { name: 'Starter', color: 'bg-blue-600', icon: '🚀' };
            case 'demo':
                return { name: 'Demo', color: 'bg-yellow-600', icon: '🎭' };
            case 'community':
            default:
                return { name: 'Community', color: 'bg-gray-600', icon: '👥' };
        }
    };

    const tierInfo = getTierInfo(tier);

    if (loading) {
        return (
            <div className={`px-2 py-1 rounded text-xs bg-gray-700 animate-pulse ${className}`}>
                ...
            </div>
        );
    }

    return (
        <Link
            to="/subscription"
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-white ${tierInfo.color} hover:opacity-90 transition-opacity ${className}`}
            title={`Current Plan: ${tierInfo.name} - Click to manage subscription`}
        >
            <span>{tierInfo.icon}</span>
            <span className="hidden sm:inline">{tierInfo.name}</span>
        </Link>
    );
};

export default SubscriptionBadge;
