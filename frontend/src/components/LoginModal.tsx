// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { API_URL } from '../config/api';
import { DemoTenant, DemoInfo } from '../types/demo';
import { isDemoEnvironment } from '../utils/environment';
import logger from '../utils/logger';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  forceOpen?: boolean; // If true, modal cannot be closed (for landing page)
}

interface DemoKeyLoginFormProps {
  demoInfo: DemoInfo;
  error: string;
  isLoading: boolean;
  loadingDemoInfo: boolean;
  forceOpen: boolean;
  onClose: () => void;
  onDemoKeyLogin: (tenantSlug?: string) => void;
}

// Extracted component for demo key login UI (DRY principle)
const DemoKeyLoginForm: React.FC<DemoKeyLoginFormProps> = ({
  demoInfo,
  error,
  isLoading,
  loadingDemoInfo,
  forceOpen,
  onClose,
  onDemoKeyLogin,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-card rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Demo Login</h2>
          {!forceOpen && (
            <button
              onClick={onClose}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 rounded">
              {error}
            </div>
          )}

          <div className="text-center mb-4">
            <p className="text-gray-600 dark:text-gray-400 mb-2">
              Welcome to the RackPlane demo environment
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              {demoInfo.tenants && demoInfo.tenants.length > 1
                ? 'Choose a demo vertical to explore'
                : 'Click below to automatically log in'}
            </p>
          </div>

          {/* Show vertical options if available */}
          {demoInfo.tenants && demoInfo.tenants.length > 1 ? (
            <div className="space-y-3">
              {demoInfo.tenants.map((tenant) => (
                <button
                  key={tenant.slug}
                  type="button"
                  onClick={() => onDemoKeyLogin(tenant.slug)}
                  className="w-full px-4 py-3 text-left bg-card border border-border rounded-lg hover:bg-accent transition disabled:opacity-50"
                  disabled={isLoading || loadingDemoInfo}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-xl">{tenant.icon}</span>
                      <div>
                        <div className="font-semibold text-foreground">
                          {tenant.name}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {tenant.description}
                        </div>
                      </div>
                    </div>
                    <span className="text-muted-foreground">→</span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => onDemoKeyLogin()}
              className="w-full px-4 py-3 text-white bg-green-600 dark:bg-green-500 rounded-md hover:bg-green-700 dark:hover:bg-green-600 transition disabled:opacity-50 font-semibold text-lg"
              disabled={isLoading || loadingDemoInfo}
            >
              {isLoading ? 'Logging in...' : '🚀 Enter Demo'}
            </button>
          )}

          {!forceOpen && (
            <button
              type="button"
              onClick={onClose}
              className="w-full px-4 py-2 text-muted-foreground bg-secondary rounded-md hover:bg-secondary/80 transition"
              disabled={isLoading}
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose, forceOpen = false }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [demoInfo, setDemoInfo] = useState<DemoInfo | null>(null);
  const [loadingDemoInfo, setLoadingDemoInfo] = useState(false);
  const { login, checkAuth } = useAuth();
  const navigate = useNavigate();

  // Check if demo mode is enabled (for Fly.io single-tenant deployments)
  const isDemoMode = process.env.REACT_APP_DEMO_MODE === 'true';
  const demoUsername = process.env.REACT_APP_DEMO_USERNAME || 'admin';
  const demoPassword = process.env.REACT_APP_DEMO_PASSWORD || 'admin';

  // Fetch demo info when modal opens (with cancellation to prevent race conditions)
  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;

    const fetchDemoInfo = async () => {
      setLoadingDemoInfo(true);
      try {
        const response = await axios.get(`${API_URL}/api/v1/auth/demo-info`);
        if (!cancelled) {
          // Validate response structure
          const data = response.data;
          if (data && typeof data === 'object' && 'demo_login_enabled' in data) {
            setDemoInfo(data as DemoInfo);
          } else {
            logger.warn('Invalid demo info response structure');
            setDemoInfo(null);
          }
        }
      } catch (err) {
        // Demo info endpoint might not exist or might fail - that's okay
        if (!cancelled) {
          setDemoInfo(null);
        }
      } finally {
        if (!cancelled) {
          setLoadingDemoInfo(false);
        }
      }
    };

    fetchDemoInfo();

    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      setUsername('');
      setPassword('');
      if (!forceOpen) {
        onClose();
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      logger.error('Login failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setUsername('');
    setPassword('');
    setError('');
    onClose();
  };

  const handleDemoModeLogin = async () => {
    setError('');
    setIsLoading(true);
    try {
      await login(demoUsername, demoPassword);
      if (!forceOpen) {
        onClose();
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      logger.error('Demo mode login failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoKeyLogin = async (tenantSlug?: string) => {
    if (!demoInfo?.demo_key) return;

    setError('');
    setIsLoading(true);
    try {
      let loginUrl = `${API_URL}/api/v1/auth/demo-login?key=${encodeURIComponent(demoInfo.demo_key)}`;
      if (tenantSlug) {
        loginUrl += `&tenant=${encodeURIComponent(tenantSlug)}`;
      }

      const response = await axios.get(loginUrl);

      const token = response.data.access_token;
      if (token) {
        // Store token with error handling (localStorage can throw)
        try {
          localStorage.setItem('auth_token', token);
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        } catch (storageError) {
          logger.error('Failed to store token in localStorage:', storageError);
          // Token is still set in memory, but won't persist
          // Continue with login - user will need to re-login on refresh
        }

        // Trigger auth check and navigate instead of full page reload
        try {
          await checkAuth();
          navigate('/dashboard');
        } catch (authError) {
          logger.error('Auth check failed after demo login:', authError);
          // Fallback to reload if navigation fails
          window.location.href = '/dashboard';
        }
      } else {
        throw new Error('No access token in response');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error
        ? err.message
        : (axios.isAxiosError(err)
          ? err.response?.data?.detail || 'Demo login failed'
          : 'Demo login failed');
      setError(errorMessage);
      logger.error('Demo key login failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  // Demo-only mode: Show only demo login button (no username/password form)
  // Check this FIRST - it's the preferred method (dynamic from API)
  if (demoInfo?.demo_login_enabled && demoInfo.demo_key) {
    return (
      <DemoKeyLoginForm
        demoInfo={demoInfo}
        error={error}
        isLoading={isLoading}
        loadingDemoInfo={loadingDemoInfo}
        forceOpen={forceOpen}
        onClose={handleClose}
        onDemoKeyLogin={handleDemoKeyLogin}
      />
    );
  }

  // Legacy demo mode: Show credentials and auto-login button (for build-time env var)
  if (isDemoMode) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-card rounded-lg shadow-xl max-w-md w-full mx-4">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Demo Login</h2>
            {!forceOpen && (
              <button
                onClick={handleClose}
                className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Demo Credentials */}
          <div className="p-6 space-y-4">
            {error && (
              <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 rounded">
                {error}
              </div>
            )}

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Demo Credentials</h3>
              <div className="space-y-2 font-mono text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Username:</span>
                  <span className="font-bold text-gray-900 dark:text-white">{demoUsername}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Password:</span>
                  <span className="font-bold text-gray-900 dark:text-white">{demoPassword}</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleDemoModeLogin}
              className="w-full px-4 py-3 text-white bg-blue-600 dark:bg-blue-500 rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition disabled:opacity-50 font-semibold"
              disabled={isLoading}
            >
              {isLoading ? 'Logging in...' : 'Login to Demo'}
            </button>

            {!forceOpen && (
              <button
                onClick={handleClose}
                className="w-full px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition"
                disabled={isLoading}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }


  // Normal mode: Show login form
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 bg-card text-card-foreground rounded-lg shadow-xl max-w-md w-full mx-4 border border-border">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-2xl font-bold text-card-foreground">Login</h2>
          {!forceOpen && (
            <button
              onClick={handleClose}
              className="text-muted-foreground hover:text-foreground transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-foreground mb-2">
              Username
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field bg-white dark:bg-slate-950 text-slate-900 dark:text-white w-full"
              required
              autoFocus
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field bg-white dark:bg-slate-950 text-slate-900 dark:text-white w-full"
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              className="btn-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </div>

          {isDemoEnvironment() && (
            <div className="mt-4 text-center pb-2">
              <a href="/demo" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                Try the Demo Version
              </a>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default LoginModal;
