/**
 * Catalog Submission Status Constants
 * 
 * Keep these in sync with backend/app/api/v1/catalog_submissions.py
 */

export const SUBMISSION_STATUS = {
    PENDING: 'pending',
    TENANT_APPROVED: 'tenant_approved',
    APPROVED: 'approved',
    REJECTED: 'rejected',
} as const;

export type SubmissionStatusType = typeof SUBMISSION_STATUS[keyof typeof SUBMISSION_STATUS];

/**
 * Human-readable labels for each status
 */
export const STATUS_LABELS: Record<SubmissionStatusType, string> = {
    [SUBMISSION_STATUS.PENDING]: 'Pending',
    [SUBMISSION_STATUS.TENANT_APPROVED]: 'Tenant Approved',
    [SUBMISSION_STATUS.APPROVED]: 'Approved',
    [SUBMISSION_STATUS.REJECTED]: 'Rejected',
};

/**
 * Badge styling classes for each status
 */
export const STATUS_BADGE_CLASSES: Record<SubmissionStatusType, string> = {
    [SUBMISSION_STATUS.PENDING]: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    [SUBMISSION_STATUS.TENANT_APPROVED]: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    [SUBMISSION_STATUS.APPROVED]: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    [SUBMISSION_STATUS.REJECTED]: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

/**
 * Helper to get badge class with fallback for unknown status
 */
export function getStatusBadgeClass(status: string): string {
    return STATUS_BADGE_CLASSES[status as SubmissionStatusType] || 'bg-gray-100 text-gray-800';
}

/**
 * Helper to get status label with fallback for unknown status
 */
export function getStatusLabel(status: string): string {
    return STATUS_LABELS[status as SubmissionStatusType] || status;
}
