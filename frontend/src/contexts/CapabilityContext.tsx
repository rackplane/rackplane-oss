import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from './AuthContext';
import logger from '../utils/logger';

interface Capabilities {
    build_mode: 'oss' | 'premium';
    tier: string;
    features: Record<string, any>;
}

interface CapabilityContextType {
    capabilities: Capabilities | null;
    isLoading: boolean;
    checkCapability: (feature: string) => boolean;
    getFeature: (feature: string) => any;
    refreshCapabilities: () => Promise<void>;
}

const CapabilityContext = createContext<CapabilityContextType | undefined>(undefined);

export const useCapabilities = () => {
    const context = useContext(CapabilityContext);
    if (!context) {
        throw new Error('useCapabilities must be used within a CapabilityProvider');
    }
    return context;
};

interface CapabilityProviderProps {
    children: ReactNode;
}

export const CapabilityProvider: React.FC<CapabilityProviderProps> = ({ children }) => {
    const { isAuthenticated, token } = useAuth();
    const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Default capabilities for unauthenticated or initial state
    const defaultCapabilities: Capabilities = {
        build_mode: 'premium', // Assume premium by default until fetched to avoid premature hiding
        tier: 'community',
        features: {}
    };

    const fetchCapabilities = async () => {
        if (!isAuthenticated || !token) {
            setCapabilities(null);
            setIsLoading(false);
            return;
        }

        try {
            const response = await axios.get(`${API_URL}/api/v1/capabilities`);
            setCapabilities(response.data);
            logger.debug('Capabilities loaded:', response.data);
        } catch (error) {
            logger.error('Failed to fetch capabilities:', error);
            // Fallback to default if fetch fails (e.g. network error)
            // but don't override if we already have data
            if (!capabilities) {
                setCapabilities(defaultCapabilities);
            }
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchCapabilities();
    }, [isAuthenticated, token]);

    const checkCapability = (feature: string): boolean => {
        // If loading, assume false? Or true? 
        // Usually false prevents rendering premium features prematurely.
        if (!capabilities) return false;

        const featureValue = capabilities.features[feature];

        // Feature can be boolean or object (e.g., { enabled: true, limit: 100 })
        if (typeof featureValue === 'boolean') {
            return featureValue;
        }

        if (typeof featureValue === 'object' && featureValue !== null && 'enabled' in featureValue) {
            return !!featureValue.enabled;
        }

        return false;
    };

    const getFeature = (feature: string): any => {
        if (!capabilities) return null;
        return capabilities.features[feature];
    };

    const value = {
        capabilities,
        isLoading,
        checkCapability,
        getFeature,
        refreshCapabilities: fetchCapabilities
    };

    return <CapabilityContext.Provider value={value}>{children}</CapabilityContext.Provider>;
};
