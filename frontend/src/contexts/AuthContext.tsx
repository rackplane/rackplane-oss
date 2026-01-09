// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface User {
  id: number;
  username: string;
  is_active: boolean;
  is_super_admin?: boolean;
  role?: string; // 'super_admin', 'tenant_admin', 'user', 'read_only'
  ui_preferences?: Record<string, any>;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  isTenantAdmin: boolean; // TENANT_ADMIN or SUPER_ADMIN
  isLoading: boolean;
  isTransitioning: boolean; // True when switching between verticals/demos
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [isLoading, setIsLoading] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [urlSearchParams, setUrlSearchParams] = useState<string>(window.location.search);

  // Configure axios to include token in all requests
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check authentication status and user profile
  const checkAuth = async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      // First check if token is valid
      // Use /me endpoint directly as it's more reliable than /check
      // /check might have redirect issues with trailing slashes
      const checkResponse = await axios.get(`${API_URL}/api/v1/auth/me`);
      if (checkResponse.data) {
        const userData = checkResponse.data;
        setUser({
          id: userData.id,
          username: userData.username,
          is_active: userData.is_active,
          is_super_admin: userData.is_super_admin || false,
          role: userData.role || 'user',
          ui_preferences: userData.ui_preferences
        });
        // User is authenticated and has profile - all good
      } else {
        // No user data returned
        setUser(null);
        setToken(null);
        localStorage.removeItem('auth_token');
      }
    } catch (error: any) {
      // Only clear token on 401 Unauthorized (actual auth failure)
      // Don't clear for network errors, timeouts, or server errors
      const status = error.response?.status;
      if (status === 401 || status === 403) {
        logger.warn('Auth check returned 401/403, clearing token');
        setUser(null);
        setToken(null);
        localStorage.removeItem('auth_token');
      } else if (status === 307 || status === 308) {
        // Redirect error - try without trailing slash or handle redirect
        logger.warn('Auth check got redirect, retrying with different path');
        try {
          // Try with trailing slash if original didn't have it, or vice versa
          const altPath = `${API_URL}/api/v1/auth/me`.endsWith('/')
            ? `${API_URL}/api/v1/auth/me`.slice(0, -1)
            : `${API_URL}/api/v1/auth/me/`;
          const retryResponse = await axios.get(altPath);
          if (retryResponse.data) {
            const userData = retryResponse.data;
            setUser({
              id: userData.id,
              username: userData.username,
              is_active: userData.is_active,
              is_super_admin: userData.is_super_admin || false,
              role: userData.role || 'user'
            });
            return; // Success, exit early (isLoading handled in finally?) 
            // Wait, finally block sets isLoading(false). This return works.
          }
        } catch (retryError: any) {
          // Retry also failed, fall through to error handling
          logger.warn('Auth check retry also failed:', retryError.response?.status);
        }
        // If retry failed, keep token but don't set user (will show as not authenticated)
        // This prevents logout on redirect issues
        logger.warn('Auth check failed (redirect issue), keeping token but not setting user');
      } else {
        // Network error or server error - keep token, assume user is still authenticated
        // This prevents logout on temporary network issues
        logger.warn('Auth check failed (non-auth error), keeping token:', status || 'no response');
        // If we have a token but can't verify, assume still valid
        // User will be re-verified on next successful request
      }
    } finally {
      // If we have a demo key and NO user/token yet, keep loading to allow demo login to proceed
      // This prevents App.tsx from rendering unauth routes which redirect/strip params
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('demo_key') && !token) {
        logger.info('Demo key detected, deferring loading state update');
      } else {
        setIsLoading(false);
      }
    }
  };

  // Validate demo key and tenant parameters (security: sanitize input)
  const validateDemoParams = (demoKey: string | null, demoTenant: string | null): { isValid: boolean; key: string | null; tenant: string | null } => {
    if (!demoKey) {
      return { isValid: false, key: null, tenant: null };
    }

    // Validate demo key: alphanumeric, dashes, underscores only, max 100 chars
    const keyPattern = /^[a-zA-Z0-9_-]{1,100}$/;
    if (!keyPattern.test(demoKey)) {
      logger.warn('Invalid demo key format, ignoring');
      return { isValid: false, key: null, tenant: null };
    }

    // Validate tenant: alphanumeric, dashes, underscores only, max 50 chars
    let validatedTenant: string | null = null;
    if (demoTenant) {
      const tenantPattern = /^[a-zA-Z0-9_-]{1,50}$/;
      if (!tenantPattern.test(demoTenant)) {
        logger.warn('Invalid tenant format, ignoring tenant parameter');
      } else {
        validatedTenant = demoTenant;
      }
    }

    return { isValid: true, key: demoKey, tenant: validatedTenant };
  };

  // Track URL search params changes (for demo login)
  // Use a ref to track the last processed search string to avoid infinite loops
  const lastProcessedSearchRef = useRef<string>(window.location.search);
  
  useEffect(() => {
    const checkSearchParams = () => {
      const currentSearch = window.location.search;
      if (currentSearch !== lastProcessedSearchRef.current) {
        lastProcessedSearchRef.current = currentSearch;
        setUrlSearchParams(currentSearch);
      }
    };
    
    // Check immediately on mount
    checkSearchParams();
    
    // Listen for browser navigation (back/forward buttons)
    window.addEventListener('popstate', checkSearchParams);
    
    // Poll for changes (reduced frequency for better performance)
    // This handles cases where URL is modified programmatically
    // 500ms is sufficient - most URL changes are caught by popstate event
    const interval = setInterval(checkSearchParams, 500);
    
    return () => {
      window.removeEventListener('popstate', checkSearchParams);
      clearInterval(interval);
    };
  }, []); // Only run once on mount

  // Auto-login with demo key if present in URL
  // Allows switching between vertical demos even when already logged in
  useEffect(() => {
    const urlParams = new URLSearchParams(urlSearchParams);
    const demoKey = urlParams.get('demo_key');
    const demoTenant = urlParams.get('tenant');

    const validation = validateDemoParams(demoKey, demoTenant);
    if (!validation.isValid || !validation.key) {
      return;
    }

    // TypeScript: At this point, validation.key is guaranteed to be a string
    const validatedKey: string = validation.key;
    const validatedTenant: string | null = validation.tenant;

    // Only allow demo login if:
    // 1. No existing token (first login), OR
    // 2. User is already on a demo (has demo_key in URL) - allows vertical switching
    const isAlreadyOnDemo = urlParams.has('demo_key');
    const shouldAllowDemoLogin = !token || isAlreadyOnDemo;

    if (!shouldAllowDemoLogin) {
      // Security: Don't allow demo login to hijack existing sessions
      // unless user is already on a demo
      logger.warn('Demo login blocked: existing session without demo context');
      urlParams.delete('demo_key');
      urlParams.delete('tenant');
      window.history.replaceState({}, '', window.location.pathname);
      // Update state to reflect URL change (popstate doesn't fire on replaceState)
      setUrlSearchParams('');
      return;
    }

    const performDemoLogin = async () => {
      setIsTransitioning(true);
      try {
        logger.info('Attempting demo auto-login...');

        // Clear existing state atomically to prevent UI flicker
        const oldToken = token;
        if (oldToken) {
          localStorage.removeItem('auth_token');
          delete axios.defaults.headers.common['Authorization'];
        }
        setUser(null);
        setToken(null);

        // Build demo login URL with validated tenant
        let demoLoginUrl = `${API_URL}/api/v1/auth/demo-login?key=${encodeURIComponent(validatedKey)}`;
        if (validatedTenant) {
          demoLoginUrl += `&tenant=${encodeURIComponent(validatedTenant)}`;
          logger.info(`Demo login for tenant: ${validatedTenant}`);
        }

        const response = await axios.get(demoLoginUrl);

        const newToken = response.data.access_token;
        if (!newToken) {
          throw new Error('No access token in response');
        }

        // Update token atomically (with error handling for localStorage)
        try {
          localStorage.setItem('auth_token', newToken);
        } catch (storageError) {
          logger.error('Failed to store token in localStorage:', storageError);
          // Token is still set in memory, but won't persist
          // Continue with login - user will need to re-login on refresh
        }
        axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        setToken(newToken);

        // Remove demo_key and tenant from URL
        urlParams.delete('demo_key');
        urlParams.delete('tenant');
        const newUrl = window.location.pathname + (urlParams.toString() ? `?${urlParams.toString()}` : '');
        window.history.replaceState({}, '', newUrl);
        // Update state to reflect URL change (popstate doesn't fire on replaceState)
        setUrlSearchParams(urlParams.toString() ? `?${urlParams.toString()}` : '');

        logger.info('Demo auto-login successful');
      } catch (error: unknown) {
        // Sanitize error messages before logging (security)
        let errorMessage = 'Unknown error';
        if (axios.isAxiosError(error)) {
          errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
        } else if (error instanceof Error) {
          errorMessage = error.message;
        }
        
        const sanitizedError = typeof errorMessage === 'string' 
          ? errorMessage.substring(0, 200) // Limit length
          : 'Authentication failed';
        
        logger.error('Demo auto-login failed:', sanitizedError);
        
        // Clear state on error
        setUser(null);
        setToken(null);
        try {
          localStorage.removeItem('auth_token');
        } catch (storageError) {
          logger.error('Failed to remove token from localStorage:', storageError);
        }
        delete axios.defaults.headers.common['Authorization'];
        
        // Remove invalid demo_key from URL
        urlParams.delete('demo_key');
        urlParams.delete('tenant');
        window.history.replaceState({}, '', window.location.pathname);
        // Update state to reflect URL change (popstate doesn't fire on replaceState)
        setUrlSearchParams('');
      } finally {
        setIsTransitioning(false);
      }
    };

    performDemoLogin();
  }, [urlSearchParams, token]); // Rerun when URL search params or token changes

  // Check auth on mount and when token changes
  useEffect(() => {
    checkAuth();
  }, [token]);

  const login = async (username: string, password: string) => {
    try {
      // OAuth2 expects form data, not JSON
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      // Convert URLSearchParams to string for axios
      const response = await axios.post(
        `${API_URL}/api/v1/auth/login`,
        formData.toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      const newToken = response.data.access_token;
      if (!newToken) {
        throw new Error('No access token in response');
      }

      localStorage.setItem('auth_token', newToken);

      // Set axios header immediately before making any authenticated requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;

      // Set token state - this will trigger useEffect to call checkAuth
      setToken(newToken);

      // Fetch user info immediately (don't wait for useEffect)
      try {
        const checkResponse = await axios.get(`${API_URL}/api/v1/auth/check`);
        logger.debug('Auth check response:', checkResponse.data);

        if (checkResponse.data.authenticated && checkResponse.data.user) {
          // Map the response to match User interface
          const userData = checkResponse.data.user;
          setUser({
            id: userData.id,
            username: userData.username,
            is_active: userData.is_active,
            is_super_admin: userData.is_super_admin || false,
            role: userData.role || 'user'
          });
          setIsLoading(false);
          return; // Success - exit early
        }
      } catch (checkError: any) {
        logger.error('Auth check failed, trying /me endpoint:', checkError);
      }

      // Fallback to /api/v1/auth/me if check fails
      try {
        const meResponse = await axios.get(`${API_URL}/api/v1/auth/me`);
        logger.debug('Auth me response:', meResponse.data);
        setUser({
          id: meResponse.data.id,
          username: meResponse.data.username,
          is_active: meResponse.data.is_active,
          is_super_admin: meResponse.data.is_super_admin || false,
          role: meResponse.data.role || 'user',
          ui_preferences: meResponse.data.ui_preferences
        });
        setIsLoading(false);
      } catch (meError: any) {
        logger.error('Failed to fetch user info from /me:', meError);
        // Token is valid but can't get user info - still allow login with minimal user
        setUser({
          id: 0,
          username: username,
          is_active: true,
          is_super_admin: false
        } as User);
        setIsLoading(false);
      }
    } catch (error: any) {
      logger.error('Login failed:', error);
      setUser(null);
      setToken(null);
      localStorage.removeItem('auth_token');
      setIsLoading(false);
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
    delete axios.defaults.headers.common['Authorization'];
  };

  // Check if user is tenant admin or super admin
  const isTenantAdmin = !!(user && (
    user.is_super_admin ||
    user.role === 'super_admin' ||
    user.role === 'tenant_admin'
  ));

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user,
    isSuperAdmin: !!(user?.is_super_admin || user?.role === 'super_admin'),
    isTenantAdmin,
    isLoading,
    isTransitioning,
    login,
    logout,
    checkAuth
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
