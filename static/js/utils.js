/**
 * Discussion Den - Utility Functions
 * Centralized utilities to prevent code duplication and ensure consistency
 */

/**
 * Format time ago string - matches server-side timeago filter logic exactly
 * 
 * IMPORTANT: This function assumes dateString is a UTC timestamp from the server.
 * All database timestamps are stored as UTC via datetime.utcnow().
 * 
 * @param {string} dateString - ISO datetime string from server (UTC)
 * @returns {string} - Formatted time ago string (e.g., "2h ago", "3d ago")
 */
function formatTimeAgo(dateString) {
    if (!dateString) {
        return 'unknown';
    }
    
    try {
        // Parse ISO string as UTC (server sends UTC timestamps)
        // Add 'Z' suffix if not present to ensure UTC parsing
        const date = new Date(dateString + (dateString.includes('Z') ? '' : 'Z'));
        const now = new Date();
        
        // Validate parsed date
        if (isNaN(date.getTime())) {
            return 'unknown';
        }
        
        // Calculate difference in milliseconds
        const diffMs = now.getTime() - date.getTime();
        
        // Handle future dates (clock skew protection)
        if (diffMs < 0) {
            return 'just now';
        }
        
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffSeconds / 3600);
        const diffDays = Math.floor(diffSeconds / 86400);
        
        // Match server-side timeago filter logic exactly
        if (diffDays > 365) {
            const years = Math.floor(diffDays / 365);
            return `${years}y ago`;
        } else if (diffDays > 30) {
            const months = Math.floor(diffDays / 30);
            return `${months}mo ago`;
        } else if (diffDays > 7) {
            const weeks = Math.floor(diffDays / 7);
            return `${weeks}w ago`;
        } else if (diffDays > 0) {
            return `${diffDays}d ago`;
        } else if (diffHours > 0) {
            return `${diffHours}h ago`;
        } else if (diffMins > 0) {
            return `${diffMins}m ago`;
        }
        
        return 'just now';
        
    } catch (error) {
        console.warn('Error formatting time ago:', error, 'dateString:', dateString);
        return 'unknown';
    }
}

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} - HTML-escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get CSRF token from meta tag or form input
 * @returns {string} - CSRF token or empty string
 */
function getCSRFToken() {
    // Try meta tag first
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    
    // Fallback: try form input
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    return '';
}