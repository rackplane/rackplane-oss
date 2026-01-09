// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Reusable formatting utilities

/**
 * Format a date string for display.
 * Returns '-' if the date is null/undefined.
 */
export const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
};

/**
 * Format a date string with time for display.
 * Returns '-' if the date is null/undefined.
 */
export const formatDateTime = (dateString: string | null | undefined): string => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
};

/**
 * Format a currency amount for display.
 * Returns '-' if the amount is null/undefined.
 * @param amount - The amount to format
 * @param currency - ISO 4217 currency code (default: 'USD')
 */
export const formatCurrency = (
    amount: number | null | undefined,
    currency: string = 'USD'
): string => {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
    }).format(amount);
};

/**
 * Format a number with commas for display.
 * Returns '-' if the number is null/undefined.
 */
export const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat('en-US').format(num);
};

/**
 * Format a percentage for display.
 * Returns '-' if the number is null/undefined.
 * @param num - The decimal value (0.5 = 50%)
 * @param decimals - Number of decimal places (default: 1)
 */
export const formatPercent = (
    num: number | null | undefined,
    decimals: number = 1
): string => {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    }).format(num);
};
