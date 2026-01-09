// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * Shared formatting utilities for slug-to-display-name conversion.
 * Centralizes acronym handling and provides helper functions used by
 * formatStatus and formatAssetType.
 */

/**
 * Centralized list of acronyms that should be displayed in UPPERCASE.
 * Add new acronyms here to ensure consistent handling across all formatters.
 */
export const ACRONYMS = new Set([
    // Asset types
    'dac', 'aoc', 'pdu', 'ups', 'ssd', 'hdd', 'nvme', 'gpu', 'cpu', 'nic',
    // Status abbreviations
    'rma', 'id', 'ip', 'dc',
    // Common IT acronyms
    'usb', 'led', 'lcd', 'api', 'url', 'ram', 'rom', 'lan', 'wan', 'vpn',
]);

/**
 * Capitalizes a word, handling acronyms appropriately.
 * 
 * @param word - A lowercase word to capitalize
 * @returns The word in Title Case, or UPPERCASE if it's a known acronym
 * 
 * @example
 * capitalizeWord('cable') // Returns 'Cable'
 * capitalizeWord('dac') // Returns 'DAC'
 * capitalizeWord('rma') // Returns 'RMA'
 */
export function capitalizeWord(word: string): string {
    if (ACRONYMS.has(word.toLowerCase())) {
        return word.toUpperCase();
    }
    return word.charAt(0).toUpperCase() + word.slice(1);
}

/**
 * Converts a snake_case slug to a Title Case display string.
 * Handles acronyms appropriately using the centralized ACRONYMS set.
 * 
 * @param slug - A snake_case string (e.g., 'dac_cable')
 * @returns A Title Case string (e.g., 'DAC Cable')
 * 
 * @example
 * snakeCaseToTitleCase('dac_cable') // Returns 'DAC Cable'
 * snakeCaseToTitleCase('in_storage') // Returns 'In Storage'
 * snakeCaseToTitleCase('rma') // Returns 'RMA'
 */
export function snakeCaseToTitleCase(slug: string): string {
    return slug
        .split('_')
        .map(capitalizeWord)
        .join(' ');
}

/**
 * Derives a list of option objects from a labels record.
 * Use this to create dropdown options from a labels map, ensuring
 * the labels stay in sync with a single source of truth.
 * 
 * @param labelsMap - A Record mapping slug values to display labels
 * @param keys - An array of keys to include in the options (subset of labelsMap keys)
 * @returns An array of { value, label } objects
 * 
 * @example
 * const labels = { server: 'Server', switch: 'Switch' };
 * deriveOptions(labels, ['server']); // Returns [{ value: 'server', label: 'Server' }]
 */
export function deriveOptions<T extends Record<string, string>>(
    labelsMap: T,
    keys: Array<keyof T>
): Array<{ value: string; label: string }> {
    return keys.map((key) => ({
        value: String(key),
        label: labelsMap[key],
    }));
}
