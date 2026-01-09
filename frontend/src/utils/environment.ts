/**
 * Environment utilities
 */

/**
 * Checks if the current environment is the public demo site.
 * Used to toggle specific behaviors like routing to the vertical selector instead of login.
 */
export const isDemoEnvironment = (): boolean => {
    if (typeof window === 'undefined') return false;


    // Strict Opt-In: Only show Demo UI if explicitly requested via env var.
    // We removed hostname checks (demo.*, .fly.dev) to prevent accidental
    // exposure on customer/production environments.
    return process.env.REACT_APP_IS_DEMO === 'true';
};
