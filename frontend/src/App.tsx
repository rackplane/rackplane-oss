// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0
// OSS Version - Premium features excluded

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { CapabilityProvider, useCapabilities } from './contexts/CapabilityContext';
import { WhiteLabelProvider, useWhiteLabel } from './contexts/WhiteLabelContext';
import { CartProvider, useCart } from './contexts/CartContext';
import ShoppingCartDrawer from './components/ShoppingCartDrawer';
import { API_URL } from './config/api';
import axios from 'axios';
import logger from './utils/logger';
import {
    ALL_NAV_ITEMS,
    NAV_GROUPS,
    NavItem
} from './config/navigation';
import CableScanner from './components/CableScanner';
import CableAssemblyManager from './components/CableAssemblyManager';
import LoginModal from './components/LoginModal';
import ProtectedRoute from './components/ProtectedRoute';
import SuperAdminRoute from './components/SuperAdminRoute';
import ConditionalDashboard from './components/ConditionalDashboard';
import GlobalSearch from './components/GlobalSearch';
import ThemeToggle from './components/ThemeToggle';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

const AdminDashboard = React.lazy(() => import('./pages/AdminDashboard'));
const Assets = React.lazy(() => import('./pages/Assets'));
const AssetDetail = React.lazy(() => import('./pages/AssetDetail'));
const AssetTypes = React.lazy(() => import('./pages/AssetTypes'));
const Locations = React.lazy(() => import('./pages/Locations'));
const Racks = React.lazy(() => import('./pages/Racks'));
const StorageContainers = React.lazy(() => import('./pages/StorageContainers'));
const ContainerDetail = React.lazy(() => import('./pages/ContainerDetail'));
const Maintenance = React.lazy(() => import('./pages/Maintenance'));
const Reports = React.lazy(() => import('./pages/Reports'));
// NetBox removed for OSS
const Backup = React.lazy(() => import('./pages/Backup'));
const DiagnosticPage = React.lazy(() => import('./pages/DiagnosticPage'));
const EnvironmentTroubleshooting = React.lazy(() => import('./pages/EnvironmentTroubleshooting'));
const EnvironmentDetail = React.lazy(() => import('./pages/EnvironmentDetail'));
const Users = React.lazy(() => import('./pages/Users'));
// Tenants removed for OSS
const Onboarding = React.lazy(() => import('./pages/Onboarding'));
const RackDetail = React.lazy(() => import('./pages/RackDetail'));
const MobileDCMS = React.lazy(() => import('./pages/MobileDCMS'));
const ConnectionsList = React.lazy(() => import('./pages/ConnectionsList'));
const StockManagement = React.lazy(() => import('./pages/StockManagement'));

const CSVImportExport = React.lazy(() => import('./pages/CSVImportExport'));
const AuditLogs = React.lazy(() => import('./pages/AuditLogs'));
const VendorSKUs = React.lazy(() => import('./pages/VendorSKUs'));
const Settings = React.lazy(() => import('./pages/Settings'));
// ServiceContracts removed for OSS
const PortTemplates = React.lazy(() => import('./pages/PortTemplates'));
// Subscription removed for OSS
// WhiteLabelSettings removed for OSS
// DemoLanding removed for OSS
const Checkout = React.lazy(() => import('./pages/Checkout'));
const CatalogSubmissions = React.lazy(() => import('./pages/CatalogSubmissions'));

const RedirectToPricing = () => {
    useEffect(() => { window.location.href = 'https://rackplane.com/pricing'; }, []);
    return <div className="flex items-center justify-center h-screen">Redirecting to pricing...</div>;
};

const LandingPage = () => {
    const [showLoginModal, setShowLoginModal] = useState(true);

    return (
        <div className="min-h-screen flex items-center justify-center p-4">
            <div className="text-center max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-xl p-8">
                <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-4">Welcome to RackPlane</h1>
                <p className="text-gray-600 dark:text-gray-300 mb-6">
                    Please log in to access the application.
                </p>
                <div className="space-y-4">
                    <LoginModal
                        isOpen={showLoginModal}
                        onClose={() => setShowLoginModal(false)}
                    />

                    {!showLoginModal && (
                        <button
                            onClick={() => setShowLoginModal(true)}
                            className="w-full btn-primary mb-4"
                        >
                            Login
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

// Constants
const DROPDOWN_CLOSE_DELAY_MS = 200;

function AppContent() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [openDropdown, setOpenDropdown] = useState<string | null>(null);
    const [loginModalOpen, setLoginModalOpen] = useState(false);
    const [searchModalOpen, setSearchModalOpen] = useState(false);
    const [showDevTroubleshooting, setShowDevTroubleshooting] = useState(false);  // Default: OFF
    const dropdownCloseTimerRef = useRef<NodeJS.Timeout | null>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const { capabilities } = useCapabilities();
    const { user, isAuthenticated, isSuperAdmin, isTenantAdmin, logout } = useAuth();
    const { displayName, t } = useWhiteLabel();
    const { toggleCart, cart } = useCart();

    const getTranslatedLabel = useCallback((item: NavItem) => {
        switch (item.id) {
            case 'inventory': return t('items');
            case 'stock': return `${t('stock')} Status`;
            case 'racks': return `${t('bins')} Visualizations`;
            case 'storage': return t('storage');
            case 'asset-types': return `${t('item')} Types`;
            default: return item.label;
        }
    }, [t]);

    // Load and listen for tenant settings changes
    useEffect(() => {
        // Load tenant settings from API (tenant-wide)
        const fetchTenantSettings = async () => {
            if (isAuthenticated) {
                // Tenant settings are not available in OSS
                setShowDevTroubleshooting(false);
                sessionStorage.setItem('tenant_enable_debug_logs', 'false');
            }
        };

        fetchTenantSettings();

        // Listen for settings changes
        const handleSettingsChange = (event: CustomEvent) => {
            if (event.detail?.showDevTroubleshooting !== undefined) {
                setShowDevTroubleshooting(event.detail.showDevTroubleshooting);
            }
        };

        window.addEventListener('settingsChanged', handleSettingsChange as EventListener);

        // Keyboard shortcut for search (Ctrl+K or Cmd+K)
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                setSearchModalOpen(true);
            }
        };

        window.addEventListener('keydown', handleKeyDown);

        return () => {
            window.removeEventListener('settingsChanged', handleSettingsChange as EventListener);
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [isAuthenticated]);

    const toggleMobileMenu = () => {
        setMobileMenuOpen(!mobileMenuOpen);
    };

    const closeMobileMenu = () => {
        setMobileMenuOpen(false);
    };

    const toggleDropdown = (groupId: string) => {
        // Clear any pending close timer when opening/toggling
        if (dropdownCloseTimerRef.current) {
            clearTimeout(dropdownCloseTimerRef.current);
            dropdownCloseTimerRef.current = null;
        }
        setOpenDropdown(openDropdown === groupId ? null : groupId);
    };

    const closeDropdowns = useCallback(() => {
        if (dropdownCloseTimerRef.current) {
            clearTimeout(dropdownCloseTimerRef.current);
            dropdownCloseTimerRef.current = null;
        }
        setOpenDropdown(null);
    }, []);

    const handleDropdownMouseLeave = () => {
        dropdownCloseTimerRef.current = setTimeout(closeDropdowns, DROPDOWN_CLOSE_DELAY_MS);
    };

    // Click outside to close dropdown
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                closeDropdowns();
            }
        };

        if (openDropdown) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => {
                document.removeEventListener('mousedown', handleClickOutside);
            };
        }

        // Cleanup timer when dropdown is closed
        return () => {
            if (dropdownCloseTimerRef.current) {
                clearTimeout(dropdownCloseTimerRef.current);
            }
        };
    }, [openDropdown, closeDropdowns]);

    const handleDropdownMouseEnter = () => {
        // Cancel any pending close when mouse re-enters
        if (dropdownCloseTimerRef.current) {
            clearTimeout(dropdownCloseTimerRef.current);
            dropdownCloseTimerRef.current = null;
        }
    };

    const handleLogout = () => {
        logout();
        closeMobileMenu();
    };

    // Move these hooks BEFORE any conditional returns to satisfy React hooks rules
    const canViewItem = useCallback((item: NavItem) => {
        if (item.requiresSuperAdmin && !isSuperAdmin) return false;
        if (item.requiresTenantAdmin && !isTenantAdmin) return false;
        if (item.requiresAuth && !isAuthenticated) return false;

        // Dynamic OSS gating via premiumOnly flag
        if (capabilities?.build_mode === 'oss') {
            if (item.premiumOnly) return false;
        }

        return true;
    }, [isSuperAdmin, isTenantAdmin, isAuthenticated, capabilities]);

    const visibleItems = useMemo(() =>
        ALL_NAV_ITEMS.filter(item => canViewItem(item)),
        [canViewItem]
    );

    // Only Dashboard appears in the main nav bar - everything else is in dropdowns
    const dashboardItem = useMemo(() =>
        visibleItems.find(item => item.id === 'dashboard'),
        [visibleItems]
    );

    if (!isAuthenticated) {
        // OSS: Always show login page (no demo mode)
        return (
            <Router>
                <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex flex-col">
                    <Routes>
                        {/* Login page at root */}
                        <Route path="/" element={<LandingPage />} />

                        {/* Onboarding - accessible without login */}
                        <Route path="/onboarding" element={<Onboarding />} />

                        {/* All other routes - show login page */}
                        <Route path="*" element={<LandingPage />} />
                    </Routes>
                </div>
            </Router>
        );
    }

    return (
        <Router>
            <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col transition-colors">
                {/* Navigation Bar */}
                <nav className="bg-primary-dark dark:bg-gray-800 text-white shadow-lg sticky top-0 z-40 transition-colors">
                    <div className="container mx-auto px-4">
                        <div className="flex items-center justify-between h-16">
                            <div className="flex items-center space-x-4 md:space-x-8">
                                <h1 className="text-xl md:text-2xl font-bold">{displayName}</h1>
                                {/* Desktop Navigation */}
                                <div className="hidden md:flex space-x-2 lg:space-x-4 items-center">
                                    {/* Dashboard link */}
                                    {dashboardItem && (
                                        <Link
                                            to={dashboardItem.path}
                                            className="px-3 py-2 rounded hover:bg-primary-hover dark:hover:bg-gray-700 transition text-sm lg:text-base whitespace-nowrap"
                                        >
                                            {getTranslatedLabel(dashboardItem)}
                                        </Link>
                                    )}

                                    {/* Grouped Dropdown Menus */}
                                    {NAV_GROUPS.map(group => {
                                        const groupItems = visibleItems.filter(item => item.group === group.id);
                                        if (groupItems.length === 0) return null;

                                        return (
                                            <div
                                                key={group.id}
                                                ref={openDropdown === group.id ? dropdownRef : null}
                                                className="relative"
                                                onMouseLeave={handleDropdownMouseLeave}
                                                onMouseEnter={handleDropdownMouseEnter}
                                            >
                                                <button
                                                    onClick={() => toggleDropdown(group.id)}
                                                    className="px-3 py-2 rounded hover:bg-primary-hover dark:hover:bg-gray-700 transition text-sm lg:text-base flex items-center"
                                                >
                                                    <span className="mr-1">{group.icon}</span>
                                                    {group.label}
                                                    <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                    </svg>
                                                </button>
                                                {openDropdown === group.id && (
                                                    <div className="absolute left-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg z-50 border border-gray-200 dark:border-gray-700 max-h-[80vh] overflow-y-auto">
                                                        {groupItems.map(item => (
                                                            <Link
                                                                key={item.id}
                                                                to={item.path}
                                                                className="block px-4 py-2 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition flex items-center"
                                                                onClick={closeDropdowns}
                                                            >
                                                                <span className="mr-2">{item.icon}</span>
                                                                {getTranslatedLabel(item)}
                                                            </Link>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}

                                    {/* DEV Troubleshooting Button */}
                                    {showDevTroubleshooting && (
                                        <Link
                                            to="/dev-troubleshooting"
                                            className="px-3 py-2 rounded bg-red-600 hover:bg-red-700 transition text-sm lg:text-base font-semibold whitespace-nowrap"
                                        >
                                            DEV Troubleshoot
                                        </Link>
                                    )}
                                </div>
                            </div>

                            {/* Search and Login/Logout Button - Desktop */}
                            <div className="hidden md:flex items-center space-x-2">
                                {/* Theme Toggle */}
                                <ThemeToggle />

                                {/* Shopping Cart Button */}
                                {isAuthenticated && (
                                    <button
                                        onClick={toggleCart}
                                        className="relative px-3 py-2 rounded bg-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover transition text-sm font-semibold flex items-center"
                                        title="Shopping Cart"
                                    >
                                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                                        </svg>
                                        {cart && cart.total_items > 0 && (
                                            <span className="absolute -top-1 -right-1 bg-red-600 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                                                {cart.total_items}
                                            </span>
                                        )}
                                    </button>
                                )}
                                {/* Global Search Button */}
                                <button
                                    onClick={() => setSearchModalOpen(true)}
                                    className="px-3 py-2 rounded bg-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover transition text-sm font-semibold flex items-center"
                                    title="Search (Ctrl+K)"
                                >
                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    Search
                                </button>
                                {isAuthenticated ? (
                                    <div className="flex items-center space-x-3">
                                        <span className="text-sm text-gray-200">
                                            {user?.username}
                                        </span>
                                        <button
                                            onClick={logout}
                                            className="px-3 py-2 rounded bg-red-600 hover:bg-red-700 transition text-sm font-semibold"
                                        >
                                            Logout
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        onClick={() => setLoginModalOpen(true)}
                                        className="px-3 py-2 rounded bg-green-600 hover:bg-green-700 transition text-sm font-semibold"
                                    >
                                        Login
                                    </button>
                                )}
                            </div>

                            {/* Mobile Hamburger Button */}
                            <button
                                onClick={toggleMobileMenu}
                                className="md:hidden p-2 rounded-lg hover:bg-primary-hover dark:hover:bg-gray-700 transition focus:outline-none focus:ring-2 focus:ring-white"
                                aria-label="Toggle mobile menu"
                                aria-expanded={mobileMenuOpen}
                            >
                                {mobileMenuOpen ? (
                                    // Close icon
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                ) : (
                                    // Hamburger icon
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Mobile Menu */}
                    {mobileMenuOpen && (
                        <div className="mobile-menu animate-fade-in">
                            <div className="py-2">
                                {/* Direct/Core Navigation Items */}
                                {visibleItems.filter(i => i.group === 'core').map(item => (
                                    <Link key={item.id} to={item.path} className="mobile-menu-link" onClick={closeMobileMenu}>
                                        {item.icon} {getTranslatedLabel(item)}
                                    </Link>
                                ))}

                                {/* Grouped Navigation Sections */}
                                {NAV_GROUPS.map(group => {
                                    const groupItems = visibleItems.filter(i => i.group === group.id);
                                    if (groupItems.length === 0) return null;

                                    return (
                                        <React.Fragment key={group.id}>
                                            <div className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase mt-2">
                                                {group.icon} {group.label}
                                            </div>
                                            {groupItems.map(item => (
                                                <Link
                                                    key={item.id}
                                                    to={item.path}
                                                    className="mobile-menu-link pl-8"
                                                    onClick={closeMobileMenu}
                                                >
                                                    {item.icon} {getTranslatedLabel(item)}
                                                </Link>
                                            ))}
                                        </React.Fragment>
                                    );
                                })}

                                {/* DEV Troubleshooting */}
                                {showDevTroubleshooting && (
                                    <Link to="/dev-troubleshooting" className="mobile-menu-link bg-red-700" onClick={closeMobileMenu}>
                                        🚨 DEV Troubleshooting
                                    </Link>
                                )}

                                {/* Theme Toggle - Mobile */}
                                <div className="px-4 py-2">
                                    <ThemeToggle />
                                </div>

                                {/* Search - Mobile */}
                                <button
                                    onClick={() => {
                                        setSearchModalOpen(true);
                                        closeMobileMenu();
                                    }}
                                    className="mobile-menu-link bg-blue-700"
                                >
                                    🔍 Search
                                </button>

                                {/* Login/Logout - Mobile */}
                                <div className="px-4 py-2 border-t border-gray-700 mt-2">
                                    {isAuthenticated ? (
                                        <div>
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm text-gray-300">Logged in as: {user?.username}</span>
                                            </div>
                                            <button
                                                onClick={handleLogout}
                                                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition text-center"
                                            >
                                                Logout
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => {
                                                setLoginModalOpen(true);
                                                closeMobileMenu();
                                            }}
                                            className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded transition text-center"
                                        >
                                            Login
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </nav>

                {/* Login Modal */}
                <LoginModal isOpen={loginModalOpen} onClose={() => setLoginModalOpen(false)} />

                {/* Global Search Modal */}
                <GlobalSearch isOpen={searchModalOpen} onClose={() => setSearchModalOpen(false)} />

                {/* Main Content */}
                <main className="container mx-auto px-4 py-6 md:py-8 flex-grow">
                    <ErrorBoundary>
                        <React.Suspense fallback={
                            <div className="flex items-center justify-center py-20">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                            </div>
                        }>
                            <Routes>
                                <Route path="/" element={<ProtectedRoute><ConditionalDashboard /></ProtectedRoute>} />
                                <Route path="/admin-dashboard" element={<SuperAdminRoute><AdminDashboard /></SuperAdminRoute>} />
                                <Route path="/mobile" element={<ProtectedRoute><MobileDCMS /></ProtectedRoute>} />
                                <Route path="/assets" element={<ProtectedRoute><Assets /></ProtectedRoute>} />
                                <Route path="/assets/:id" element={<ProtectedRoute><AssetDetail /></ProtectedRoute>} />
                                <Route path="/asset-types" element={<ProtectedRoute><AssetTypes /></ProtectedRoute>} />
                                <Route path="/vendor-skus" element={<ProtectedRoute><VendorSKUs /></ProtectedRoute>} />
                                <Route path="/locations" element={<ProtectedRoute><Locations /></ProtectedRoute>} />
                                <Route path="/racks" element={<ProtectedRoute><Racks /></ProtectedRoute>} />
                                <Route path="/storage" element={<ProtectedRoute><StorageContainers /></ProtectedRoute>} />
                                <Route path="/storage-containers/:id" element={<ProtectedRoute><ContainerDetail /></ProtectedRoute>} />
                                <Route path="/stock" element={<ProtectedRoute><StockManagement /></ProtectedRoute>} />
                                <Route path="/maintenance" element={<ProtectedRoute><Maintenance /></ProtectedRoute>} />
                                <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                                {/* Service Contracts Route REMOVED */}
                                <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
                                {/* NetBox Route REMOVED */}
                                <Route path="/backup" element={<ProtectedRoute><Backup /></ProtectedRoute>} />
                                <Route path="/diagnostic" element={<SuperAdminRoute><DiagnosticPage /></SuperAdminRoute>} />
                                <Route path="/dev-troubleshooting" element={<ProtectedRoute><EnvironmentTroubleshooting /></ProtectedRoute>} />
                                <Route path="/environment/:envId" element={<ProtectedRoute><EnvironmentDetail /></ProtectedRoute>} />
                                <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
                                {/* Tenants Route REMOVED for OSS */}
                                <Route path="/onboarding" element={<Onboarding />} />
                                {/* Demo Route REMOVED for OSS */}
                                <Route path="/racks/:rackId" element={<ProtectedRoute><RackDetail /></ProtectedRoute>} />
                                <Route path="/cable-scanner" element={<ProtectedRoute><CableScanner /></ProtectedRoute>} />
                                <Route path="/cable-assemblies" element={<ProtectedRoute><CableAssemblyManager /></ProtectedRoute>} />
                                <Route path="/connections" element={<ProtectedRoute><ConnectionsList /></ProtectedRoute>} />


                                <Route path="/subscription" element={<RedirectToPricing />} />
                                <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
                                {/* WhiteLabelSettings removed for OSS */}
                                <Route path="/catalog-submissions" element={<ProtectedRoute><CatalogSubmissions /></ProtectedRoute>} />
                            </Routes>
                        </React.Suspense>
                    </ErrorBoundary>
                </main>

                {/* Footer */}
                <footer className="bg-gray-800 dark:bg-gray-900 text-white py-6 mt-auto transition-colors relative">
                    <div className="container mx-auto px-4">
                        <div className="text-center">
                            <p className="text-xs md:text-sm text-gray-400 dark:text-gray-500">
                                RackPlane Asset Management System - AI-Powered Hardware & Inventory Management
                            </p>
                        </div>
                        {/* Copyright in corner */}
                        <div className="absolute bottom-2 right-4">
                            <p className="text-xs text-gray-500 dark:text-gray-600">&copy; 2024 {displayName}</p>
                        </div>
                    </div>
                </footer>
                {/* Shopping Cart Drawer */}
                <ShoppingCartDrawer />
            </div>
        </Router>
    );
}

function App() {
    return (
        <AuthProvider>
            <CapabilityProvider>
                <WhiteLabelProvider>
                    <CartProvider>
                        <AppContent />
                    </CartProvider>
                </WhiteLabelProvider>
            </CapabilityProvider>
        </AuthProvider>
    );
}

export default App;
