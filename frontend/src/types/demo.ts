// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0
// OSS Stub - Demo types for compatibility (demo features disabled in OSS)

/**
 * Demo-related TypeScript types (stub for OSS)
 * These types are used by LoginModal but demo functionality is disabled in OSS.
 */

export interface DemoTenant {
    slug: string;
    name: string;
    vertical: string;
    description: string;
    icon: string;
}

export interface DemoInfo {
    demo_login_enabled: boolean;
    demo_key: string | null;
    auto_login_url: string | null;
    tenants?: DemoTenant[];
}
