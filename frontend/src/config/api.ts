// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


/**
 * API Configuration
 * Auto-detects the correct API URL based on how the frontend is accessed
 */

const getAPIUrl = (): string => {
  // If explicitly set via environment variable, use that
  if (process.env.REACT_APP_API_URL !== undefined && process.env.REACT_APP_API_URL !== '') {
    return process.env.REACT_APP_API_URL;
  }

  // When behind nginx reverse proxy, use relative URLs (same origin)
  // Nginx proxies /api/* to the backend, eliminating CORS issues
  // This works for both development (via nginx) and production
  return ''; // Empty string = relative URLs, uses same origin
};

export const API_URL = getAPIUrl();
