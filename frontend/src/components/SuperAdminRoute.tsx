// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ProtectedRoute from './ProtectedRoute';

interface SuperAdminRouteProps {
  children: React.ReactElement;
}

/**
 * Route component that requires super admin privileges.
 * First checks authentication, then verifies super admin status.
 */
const SuperAdminRoute: React.FC<SuperAdminRouteProps> = ({ children }) => {
  const { isSuperAdmin, isLoading } = useAuth();

  // Use ProtectedRoute to handle authentication first
  return (
    <ProtectedRoute>
      {isLoading ? (
        <div className="flex justify-center items-center h-screen">
          <div className="text-xl">Loading...</div>
        </div>
      ) : !isSuperAdmin ? (
        <div className="min-h-screen bg-page flex items-center justify-center">
          <div className="text-center max-w-md mx-auto p-6">
            <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-4">Access Denied</h1>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              This page requires super administrator privileges. Please contact your system administrator if you need access.
            </p>
            <Navigate to="/" replace />
          </div>
        </div>
      ) : (
        children
      )}
    </ProtectedRoute>
  );
};

export default SuperAdminRoute;

