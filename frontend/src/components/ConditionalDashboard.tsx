// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0
// OSS Version - Always show regular Dashboard

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Dashboard from '../pages/Dashboard';

/**
 * OSS Version: Always renders the standard Dashboard.
 * AdminDashboard is a premium feature not available in the OSS build.
 */
const ConditionalDashboard: React.FC = () => {
    const { isLoading } = useAuth();

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="text-xl text-secondary">Loading...</div>
            </div>
        );
    }

    // OSS: Always show the regular dashboard
    return <Dashboard />;
};

export default ConditionalDashboard;
