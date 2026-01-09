// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Centralized Logging Utility with User-Configurable Debug Mode
 *
 * This logger provides a centralized way to handle console logging across
 * the application with user-configurable debug mode. Debug logs can be toggled
 * on/off via Settings > Enable Debug Logs, while errors and warnings are always shown.
 *
 * Usage:
 *   import logger from '../utils/logger';
 *
 *   logger.debug('Component mounted', { props });    // Only shows when debug enabled
 *   logger.error('API call failed', error);          // Always shown
 *   logger.warn('Deprecated feature used');          // Always shown
 *   logger.info('User logged in', { username });     // Only shows when debug enabled
 *
 * Configuration:
 *   - User Setting: localStorage key 'enableDebugLogs' (true/false)
 *   - Default: ON in development (NODE_ENV=development), OFF in production
 *   - Toggle: Settings page > Enable Debug Logs
 *
 * Log Levels:
 *   - debug(): Development/troubleshooting info (user-controllable)
 *   - info(): Informational messages (user-controllable)
 *   - warn(): Warnings that should always be visible
 *   - error(): Errors that should always be visible
 */

/**
 * Check if debug logging is currently enabled.
 *
 * Priority:
 * 1. Tenant-wide setting from API (tenant_settings.enable_debug_logs)
 * 2. Default: OFF (tenant-wide setting, not per-user)
 *
 * @returns true if debug logs should be shown, false otherwise
 */
const isDebugEnabled = (): boolean => {
  // Check for tenant-wide setting (stored in sessionStorage after API fetch)
  // This is set by App.tsx or Settings.tsx after fetching from API
  const tenantSetting = sessionStorage.getItem('tenant_enable_debug_logs');
  
  if (tenantSetting !== null) {
    return tenantSetting === 'true';
  }

  // Default: OFF (tenant-wide setting)
  return false;
};

/**
 * Centralized logger instance
 */
const logger = {
  /**
   * Debug logging - only shown when enableDebugLogs is true
   *
   * Use for detailed troubleshooting information that developers
   * or power users might need but would clutter the console otherwise.
   *
   * @param message - Log message
   * @param args - Additional arguments to log
   */
  debug: (message: string, ...args: any[]): void => {
    if (isDebugEnabled()) {
      console.log(`[DEBUG] ${message}`, ...args);
    }
  },

  /**
   * Error logging - always shown
   *
   * Use for errors that users should be aware of, such as API failures,
   * validation errors, or unexpected conditions.
   *
   * @param message - Error message
   * @param args - Additional arguments to log (error objects, context, etc.)
   */
  error: (message: string, ...args: any[]): void => {
    console.error(`[ERROR] ${message}`, ...args);
  },

  /**
   * Warning logging - always shown
   *
   * Use for non-critical issues that users should be aware of,
   * such as deprecated features, edge cases, or potential problems.
   *
   * @param message - Warning message
   * @param args - Additional arguments to log
   */
  warn: (message: string, ...args: any[]): void => {
    console.warn(`[WARN] ${message}`, ...args);
  },

  /**
   * Info logging - only shown when debug is enabled
   *
   * Use for informational messages that are useful for debugging
   * but not critical errors or warnings.
   *
   * @param message - Info message
   * @param args - Additional arguments to log
   */
  info: (message: string, ...args: any[]): void => {
    if (isDebugEnabled()) {
      console.info(`[INFO] ${message}`, ...args);
    }
  }
};

export default logger;
