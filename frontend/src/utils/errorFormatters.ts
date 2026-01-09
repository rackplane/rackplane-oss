// Utility functions for formatting API errors
// Extracted from Assets.tsx and useAssetForm.ts for shared use

/**
 * Format API error responses for display to users.
 * Handles various error formats:
 * - String errors
 * - Pydantic validation errors (array of error objects)
 * - Error objects with msg property
 * 
 * @param error - The error from an API response (axios error.response.data.detail)
 * @returns A human-readable error message
 */
export const formatApiError = (error: any): string => {
    if (typeof error === 'string') {
        return error;
    }

    // Handle Pydantic validation errors (array of error objects)
    if (Array.isArray(error)) {
        return error.map(err => {
            const field = err.loc ? err.loc.join('.') : 'unknown';
            return `${field}: ${err.msg}`;
        }).join('; ');
    }

    // Handle error objects
    if (typeof error === 'object' && error.msg) {
        return error.msg;
    }

    return 'An error occurred';
};

// Alias for backward compatibility
export const formatError = formatApiError;
