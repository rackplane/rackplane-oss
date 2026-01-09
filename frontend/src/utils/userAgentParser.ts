// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

/**
 * User Agent Parser Utility
 * 
 * Parses user agent strings to extract browser/device information
 * for display in audit logs and other UI components.
 * 
 * Security Use Case:
 * - Track who did what, when, and from where (IP + device)
 * - Identify device type (phone, tablet, laptop, desktop) for security investigations
 * - Help detect unauthorized access patterns (e.g., someone accessing from unexpected device)
 */

export interface UserAgentInfo {
  browser: string;
  device: string;
  deviceType: 'phone' | 'tablet' | 'laptop' | 'desktop' | 'unknown';
  icon: string; // Emoji or icon identifier
  displayName: string;
}

/**
 * Parse a user agent string to extract browser and device information
 * 
 * @param userAgent - The user agent string to parse
 * @returns UserAgentInfo object with browser, device, deviceType, icon, and display name
 */
export function parseUserAgent(userAgent: string | null | undefined): UserAgentInfo {
  if (!userAgent) {
    return {
      browser: 'Unknown',
      device: 'Unknown',
      deviceType: 'unknown',
      icon: '❓',
      displayName: 'Unknown Device'
    };
  }

  const ua = userAgent.toLowerCase();

  // Detect device type - order matters! Check iPad before iPhone
  let device = 'Desktop';
  let deviceType: 'phone' | 'tablet' | 'laptop' | 'desktop' | 'unknown' = 'desktop';
  let deviceIcon = '💻'; // Default to laptop/desktop icon
  
  // iPad detection (must come before iPhone)
  if (ua.includes('ipad') || (ua.includes('macintosh') && ua.includes('safari') && !ua.includes('version'))) {
    // iPad on iOS 13+ reports as Macintosh, but we can detect it
    device = 'iPad';
    deviceType = 'tablet';
    deviceIcon = '📱'; // Tablet icon (iPad)
  } 
  // iPhone detection
  else if (ua.includes('iphone') || ua.includes('ipod')) {
    device = 'iPhone';
    deviceType = 'phone';
    deviceIcon = '📱'; // Phone icon
  } 
  // Android tablet detection (check for tablet keywords)
  else if (ua.includes('android')) {
    // Android tablets often include "tablet" or have specific screen size indicators
    if (ua.includes('tablet') || ua.includes('gt-') || ua.includes('sm-') || ua.includes('nexus 7') || ua.includes('nexus 9') || ua.includes('nexus 10')) {
      device = 'Android Tablet';
      deviceType = 'tablet';
      deviceIcon = '📱'; // Tablet icon
    } else {
      device = 'Android Phone';
      deviceType = 'phone';
      deviceIcon = '📱'; // Phone icon
    }
  } 
  // Other mobile devices
  else if (ua.includes('mobile') || ua.includes('blackberry') || ua.includes('windows phone')) {
    device = 'Mobile';
    deviceType = 'phone';
    deviceIcon = '📱';
  }
  // Laptop detection (heuristic - not always reliable)
  else if (ua.includes('macintosh') || ua.includes('mac os')) {
    // Mac devices are typically laptops
    device = 'Mac';
    deviceType = 'laptop';
    deviceIcon = '💻'; // Laptop icon
  } else if (ua.includes('windows')) {
    // Windows devices - try to detect laptop patterns
    // Most Windows devices in enterprise are laptops
    device = 'Windows PC';
    deviceType = 'laptop'; // Default to laptop for Windows (most common in enterprise)
    deviceIcon = '💻';
  } else if (ua.includes('linux')) {
    device = 'Linux';
    deviceType = 'desktop'; // Linux is often desktop/server
    deviceIcon = '🖥️'; // Desktop icon
  }

  // Detect browser
  let browser = 'Unknown';
  let browserIcon = '🌐';
  
  if (ua.includes('chrome') && !ua.includes('edg') && !ua.includes('opr')) {
    browser = 'Chrome';
    browserIcon = '🌐'; // Chrome icon
  } else if (ua.includes('firefox')) {
    browser = 'Firefox';
    browserIcon = '🦊';
  } else if (ua.includes('safari') && !ua.includes('chrome')) {
    browser = 'Safari';
    browserIcon = '🧭';
  } else if (ua.includes('edg')) {
    browser = 'Edge';
    browserIcon = '🌐';
  } else if (ua.includes('opr') || ua.includes('opera')) {
    browser = 'Opera';
    browserIcon = '🌐';
  } else if (ua.includes('msie') || ua.includes('trident')) {
    browser = 'IE';
    browserIcon = '🌐';
  }

  // Choose icon: prioritize device type for mobile/tablet, browser for desktop
  const icon = deviceType !== 'desktop' && deviceType !== 'laptop' ? deviceIcon : browserIcon;
  
  // Build display name
  let displayName: string;
  if (deviceType === 'phone' || deviceType === 'tablet') {
    displayName = `${device} (${browser})`;
  } else if (deviceType === 'laptop') {
    displayName = `${device} - ${browser}`;
  } else {
    displayName = `${browser} on ${device}`;
  }

  return {
    browser,
    device,
    deviceType,
    icon,
    displayName
  };
}

/**
 * Get a user-friendly display for user agent in tables
 * Returns just the icon for compact display
 */
export function getUserAgentIcon(userAgent: string | null | undefined): string {
  return parseUserAgent(userAgent).icon;
}

/**
 * Get a user-friendly display name for user agent
 */
export function getUserAgentDisplayName(userAgent: string | null | undefined): string {
  return parseUserAgent(userAgent).displayName;
}

