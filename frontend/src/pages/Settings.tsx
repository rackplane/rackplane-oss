// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FeatureGate } from '../components/FeatureGate';
import { API_URL } from '../config/api';

import logger from '../utils/logger';

import { useNavigate, useLocation } from 'react-router-dom';

// Feature flags - set to false until features are ready
// Feature flags - set to false until features are ready
// FS.com: Premium feature, controlled by backend capabilities
// Contributor Program: Designed for all users but not implemented yet
import { useCapabilities } from '../contexts/CapabilityContext';

const SHOW_CONTRIBUTOR_PROGRAM = false;

interface SettingsState {
  showDevTroubleshooting: boolean;
  enableDebugLogs: boolean;
}

interface ApiKey {
  id: number;
  user_id: number;
  label: string | null;
  last_used_at: string | null;
  is_active: boolean;
  scopes: string[] | null;
  created_at: string;
}

interface ApiKeyCreateResponse {
  id: number;
  user_id: number;
  label: string | null;
  key: string;
  is_active: boolean;
  created_at: string;
}

// Amazon Business Punchout Configuration Component
const AmazonPunchoutConfig: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState({
    enabled: false,
    identity: '',
    shared_secret: '',
    url: '',
    po_url: '',
    user_email: '',
    mode: 'test' as 'test' | 'production',
  });
  const [hasSecret, setHasSecret] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showIdentityInput, setShowIdentityInput] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/v1/punchout/amazon/status`);
        setConfig(prev => ({
          ...prev,
          enabled: response.data.enabled || false,
          mode: response.data.mode || 'test',
          url: response.data.url || '',
          po_url: response.data.po_url || '',
          user_email: response.data.user_email || '',
          identity: response.data.identity || '',
        }));
        setHasSecret(response.data.configured || false);
        if (response.data.identity) {
          setShowIdentityInput(false);
        }
      } catch (err) {
        logger.error('Failed to fetch Punchout status:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_URL}/api/v1/punchout/amazon/config`, {
        enabled: config.enabled,
        identity: config.identity || undefined,
        shared_secret: config.shared_secret || undefined,
        url: config.url || undefined,
        po_url: config.po_url || undefined,
        user_email: config.user_email || undefined,
        mode: config.mode,
      });
      setHasSecret(!!config.shared_secret || hasSecret);
      setShowForm(false);
      setConfig(prev => ({ ...prev, shared_secret: '' })); // Clear secret from memory
      alert('Amazon Business Punchout configuration saved!');
    } catch (err: any) {
      logger.error('Failed to save Punchout config:', err);
      alert(err.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading...</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 text-xs rounded-full font-medium ${hasSecret && config.enabled
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
            }`}>
            {hasSecret && config.enabled ? 'Configured' : 'Not Configured'}
          </span>
          {config.mode === 'test' && hasSecret && (
            <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 rounded-full">
              Test Mode
            </span>
          )}
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
        >
          {showForm ? 'Cancel' : hasSecret ? 'Update' : 'Configure'}
        </button>
      </div>

      {showForm && (
        <div className="mt-4 space-y-3 p-3 border rounded-lg bg-gray-50 dark:bg-gray-800">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enabled}
                onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm font-medium">Enable Punchout</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Identity (Network ID) {config.identity && !showIdentityInput && <span className="text-green-600 font-normal ml-2">✓ Configured</span>}
            </label>

            {config.identity && !showIdentityInput ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600 font-mono bg-gray-100 px-2 py-1 rounded">
                  {config.identity.substring(0, 4)}...
                </span>
                <button
                  type="button"
                  onClick={() => setShowIdentityInput(true)}
                  className="text-sm text-primary hover:underline"
                >
                  Change
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={config.identity}
                  onChange={(e) => setConfig({ ...config, identity: e.target.value })}
                  placeholder="Your Amazon Business Network ID"
                  className="input-field w-full text-sm"
                  autoComplete="off"
                  data-lpignore="true"
                />
                {config.identity && showIdentityInput && (
                  <button
                    type="button"
                    onClick={() => setShowIdentityInput(false)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Shared Secret {hasSecret && !config.shared_secret && <span className="text-green-600 font-normal ml-2">✓ Configured</span>}
            </label>

            {hasSecret && !config.shared_secret ? (
              <button
                type="button"
                onClick={() => setConfig({ ...config, shared_secret: ' ' })} // Set a dummy value to trigger the input to show, user will clear it
                className="text-sm text-primary hover:underline flex items-center gap-1"
              >
                <span>🔄 Change Secret</span>
              </button>
            ) : (
              <div className="relative">
                <input
                  type="password"
                  value={config.shared_secret || ''}
                  onChange={(e) => setConfig({ ...config, shared_secret: e.target.value })}
                  placeholder="Enter shared secret"
                  className="input-field w-full text-sm"
                  autoComplete="new-password"
                  data-lpignore="true"
                />
                {hasSecret && (
                  <button
                    type="button"
                    onClick={() => setConfig({ ...config, shared_secret: '' })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}
            <p className="text-xs text-gray-500 mt-1">Encrypted at rest with AES-128</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Punchout Request URL</label>
            <input
              type="text"
              value={config.url}
              onChange={(e) => setConfig({ ...config, url: e.target.value })}
              placeholder="https://abintegrations.amazon.com/punchout"
              className="input-field w-full text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Amazon provides this URL in your Punchout setup</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Purchase Order URL</label>
            <input
              type="text"
              value={config.po_url}
              onChange={(e) => setConfig({ ...config, po_url: e.target.value })}
              placeholder="https://https-ats.amazon-ats.com/cxml/POReceive"
              className="input-field w-full text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">URL for submitting orders to Amazon (required for checkout)</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Punchout User Email (Optional)</label>
            <input
              type="email"
              value={config.user_email || ''}
              onChange={(e) => setConfig({ ...config, user_email: e.target.value })}
              placeholder="purchasing@example.com (overrides login email)"
              className="input-field w-full text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Email address sent to Amazon (must match an Amazon Business user)</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Mode</label>
            <select
              value={config.mode}
              onChange={(e) => setConfig({ ...config, mode: e.target.value as 'test' | 'production' })}
              className="input-field w-full text-sm"
            >
              <option value="test">Test (Sandbox)</option>
              <option value="production">Production</option>
            </select>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const Settings: React.FC = () => {

  const [settings, setSettings] = useState<SettingsState>({
    showDevTroubleshooting: false,  // Default: OFF (tenant-wide)
    enableDebugLogs: false  // Default: OFF (tenant-wide)
  });

  const { capabilities } = useCapabilities();
  const isOss = capabilities?.build_mode === 'oss';

  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [newKeyLabel, setNewKeyLabel] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [useAllScopes, setUseAllScopes] = useState<boolean>(true);
  const [subscriptionTier, setSubscriptionTier] = useState<string>('free');

  // RackPlane Services API Key state
  const [rackplaneApiKeyConfigured, setRackplaneApiKeyConfigured] = useState(false);
  const [rackplaneApiKeyPreview, setRackplaneApiKeyPreview] = useState<string | null>(null);
  const [rackplaneCloudConnected, setRackplaneCloudConnected] = useState(false);
  const [rackplaneApiKeyInput, setRackplaneApiKeyInput] = useState('');
  const [savingApiKey, setSavingApiKey] = useState(false);
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);

  // License Management state
  const [licenseStatus, setLicenseStatus] = useState<any>(null);
  const [loadingLicense, setLoadingLicense] = useState(true);
  const [licenseKeyInput, setLicenseKeyInput] = useState('');
  const [activatingLicense, setActivatingLicense] = useState(false);
  const [showLicenseInput, setShowLicenseInput] = useState(false);
  const [validatingLicense, setValidatingLicense] = useState(false);
  const [licensePreview, setLicensePreview] = useState<any>(null);

  // FS.com Rate Limits
  const [fsRateLimits, setFsRateLimits] = useState<any>(null);
  const [, setLoadingFSLimits] = useState(false); // State unused, keep setter

  // Settings tab state
  type SettingsTab = 'all' | 'general' | 'license' | 'integrations' | 'printers';
  const [activeTab, setActiveTab] = useState<SettingsTab>('all');
  const navigate = useNavigate();
  const location = useLocation();

  // Sync tab with URL hash
  useEffect(() => {
    const hash = window.location.hash.replace('#', '');
    if (['all', 'general', 'license', 'integrations', 'printers'].includes(hash)) {
      setActiveTab(hash as SettingsTab);
    }
  }, [location.hash]);

  const handleTabChange = (tabId: SettingsTab) => {
    setActiveTab(tabId);
    navigate(`#${tabId}`, { replace: true });
  };

  const settingsTabs: { id: SettingsTab; label: string; icon: string }[] = [
    { id: 'all' as SettingsTab, label: 'All Settings', icon: '📋' },
    { id: 'general' as SettingsTab, label: 'General', icon: '⚙️' },
    ...(isOss ? [] : [
      { id: 'license' as SettingsTab, label: 'License', icon: '🔑' },
      { id: 'integrations' as SettingsTab, label: 'Integrations', icon: '🔌' },
      { id: 'printers' as SettingsTab, label: 'Printers', icon: '🖨️' }
    ]),
  ];

  // Available scopes
  const availableScopes = [
    { value: 'printer:read', label: 'Printer: Read', description: 'Read print jobs (GET /api/v1/print-jobs/pending)' },
    { value: 'printer:write', label: 'Printer: Write', description: 'Complete print jobs (POST /api/v1/print-jobs/{id}/complete)' },
    { value: 'printer:heartbeat', label: 'Printer: Heartbeat', description: 'Send agent heartbeat (POST /api/v1/print-jobs/agents/heartbeat)' },
    { value: 'assets:read', label: 'Assets: Read', description: 'Read assets (GET /api/v1/assets)' },
    { value: 'assets:write', label: 'Assets: Write', description: 'Create, update, delete assets (POST/PUT/DELETE /api/v1/assets)' },
  ];
  const [contributorProgramEnrolled, setContributorProgramEnrolled] = useState(false);
  const [requestingAccess, setRequestingAccess] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);

  // Check if user has paid subscription for API access
  const isPaidTier = subscriptionTier !== 'community' && subscriptionTier !== 'free' && subscriptionTier !== 'demo';

  useEffect(() => {
    // Load tenant settings from API (tenant-wide, not per-user)
    const fetchTenantSettings = async () => {
      try {
        setLoadingSettings(true);
        const response = await axios.get(`${API_URL}/api/v1/tenants/current/settings`);
        setSettings({
          showDevTroubleshooting: response.data.show_dev_troubleshooting || false,
          enableDebugLogs: response.data.enable_debug_logs || false
        });
        // Also fetch RackPlane Services API key status
        setRackplaneApiKeyConfigured(response.data.rackplane_api_key_configured || false);
        setRackplaneApiKeyPreview(response.data.rackplane_api_key_preview || null);
        setRackplaneCloudConnected(response.data.rackplane_cloud_connected || false);
        setContributorProgramEnrolled(response.data.contributor_program_enrolled || false);

        // Use tier from settings if reliable, otherwise stick to stripe status
        if (response.data.subscription_tier) {
          setSubscriptionTier(response.data.subscription_tier);
        }
      } catch (err: any) {
        logger.error('Failed to load tenant settings:', err);
        // Fallback to defaults (OFF)
        setSettings({
          showDevTroubleshooting: false,
          enableDebugLogs: false
        });
        // Reset API key state on error
        setRackplaneApiKeyConfigured(false);
        setRackplaneApiKeyPreview(null);
      } finally {
        setLoadingSettings(false);
      }
    };

    // Fetch subscription status (Stripe is primary source of truth for billing, but settings has it too)
    const fetchSubscriptionStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/v1/stripe/status`);
        // Only update if settings didn't already set it (or if this is more authoritative)
        // Actually, let's trust stripe/status for billing tier
        setSubscriptionTier(response.data.subscription_tier || 'community');
      } catch (err: any) {
        logger.error('Failed to load subscription status:', err);
        // Don't overwrite if setup by settings
      }
    };

    fetchTenantSettings();
    fetchSubscriptionStatus();
    fetchApiKeys();
    fetchLicenseStatus();
    fetchFSRateLimits(); // Try to fetch on load
  }, []);

  const fetchFSRateLimits = async () => {
    // Only attempt if configured (we might need to check settings first, but 401/403 is fine)
    setLoadingFSLimits(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/fs/rate-limit/status`);
      setFsRateLimits(response.data);
    } catch (err) {
      // Silently fail if not configured or not available
      console.log("FS Rate limits not available", err);
    } finally {
      setLoadingFSLimits(false);
    }
  };

  const fetchApiKeys = async () => {
    setLoadingKeys(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/api-keys/`);
      setApiKeys(response.data);
    } catch (error) {
      logger.error('Error fetching API keys:', error);
    } finally {
      setLoadingKeys(false);
    }
  };

  const generateApiKey = async () => {
    setGenerating(true);
    try {
      const payload: any = {
        label: newKeyLabel || null
      };

      // Only include scopes if not using "all scopes"
      if (!useAllScopes && selectedScopes.length > 0) {
        payload.scopes = selectedScopes;
      }
      // If useAllScopes is true, don't include scopes (null = all scopes)

      const response = await axios.post<ApiKeyCreateResponse>(`${API_URL}/api/v1/api-keys/`, payload);
      setNewKey(response.data.key);
      setShowKeyModal(true);
      setNewKeyLabel('');
      setSelectedScopes([]);
      setUseAllScopes(true);
      await fetchApiKeys();
    } catch (error: any) {
      logger.error('Error generating API key:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate API key. Please try again.';
      alert(`Unable to add key: ${errorMessage}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleScopeToggle = (scopeValue: string) => {
    if (selectedScopes.includes(scopeValue)) {
      setSelectedScopes(selectedScopes.filter(s => s !== scopeValue));
    } else {
      setSelectedScopes([...selectedScopes, scopeValue]);
      setUseAllScopes(false); // Automatically uncheck "all scopes" when selecting specific scopes
    }
  };

  const handleAllScopesToggle = (checked: boolean) => {
    setUseAllScopes(checked);
    if (checked) {
      setSelectedScopes([]); // Clear selected scopes when "all scopes" is enabled
    }
  };

  const revokeApiKey = async (keyId: number) => {
    if (!window.confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
      return;
    }
    try {
      await axios.delete(`${API_URL}/api/v1/api-keys/${keyId}`);
      await fetchApiKeys();
    } catch (error) {
      logger.error('Error revoking API key:', error);
      alert('Failed to revoke API key. Please try again.');
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      // Try modern Clipboard API first (requires HTTPS/secure context)
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        alert('API key copied to clipboard!');
        return;
      }

      // Fallback to older method for non-HTTPS or unsupported browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      try {
        const successful = document.execCommand('copy');
        if (successful) {
          alert('API key copied to clipboard!');
        } else {
          throw new Error('Copy command failed');
        }
      } catch (err) {
        // If all else fails, show the key in a prompt so user can manually copy
        logger.warn('Clipboard copy failed, showing manual copy option:', err);
        const userConfirmed = window.confirm(
          'Unable to copy to clipboard automatically.\n\n' +
          'The API key is:\n' + text + '\n\n' +
          'Click OK to select the text above, then press Ctrl+C (or Cmd+C on Mac) to copy.'
        );
        if (userConfirmed) {
          // Select the text in the modal
          const codeElement = document.querySelector('code');
          if (codeElement) {
            const range = document.createRange();
            range.selectNodeContents(codeElement);
            const selection = window.getSelection();
            if (selection) {
              selection.removeAllRanges();
              selection.addRange(range);
            }
          }
        }
      } finally {
        document.body.removeChild(textArea);
      }
    } catch (error) {
      logger.error('Error copying to clipboard:', error);
      // Show manual copy option as last resort
      const userConfirmed = window.confirm(
        'Unable to copy to clipboard automatically.\n\n' +
        'The API key is:\n' + text + '\n\n' +
        'Please manually select and copy the text above.'
      );
      if (userConfirmed) {
        // Try to select the text in the modal
        const codeElement = document.querySelector('code');
        if (codeElement) {
          const range = document.createRange();
          range.selectNodeContents(codeElement);
          const selection = window.getSelection();
          if (selection) {
            selection.removeAllRanges();
            selection.addRange(range);
          }
        }
      }
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  // License Management Functions
  const fetchLicenseStatus = async () => {
    setLoadingLicense(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/license/status`);
      setLicenseStatus(response.data);
    } catch (err: any) {
      logger.error('Failed to load license status:', err);
      setLicenseStatus(null);
    } finally {
      setLoadingLicense(false);
    }
  };

  const validateLicensePreview = async () => {
    if (!licenseKeyInput.trim()) {
      alert('Please enter a license key');
      return;
    }

    setValidatingLicense(true);
    try {
      const response = await axios.post(`${API_URL}/api/v1/license/validate`, {
        license_key: licenseKeyInput.trim()
      });
      setLicensePreview(response.data);
    } catch (err: any) {
      logger.error('Failed to validate license:', err);
      const errorMessage = err.response?.data?.error || err.response?.data?.detail || err.message || 'Invalid license key';
      alert(`License validation failed: ${errorMessage}`);
      setLicensePreview(null);
    } finally {
      setValidatingLicense(false);
    }
  };

  const activateLicense = async () => {
    if (!licenseKeyInput.trim()) {
      alert('Please enter a license key');
      return;
    }

    setActivatingLicense(true);
    try {
      const response = await axios.post(`${API_URL}/api/v1/license/activate`, {
        license_key: licenseKeyInput.trim()
      });

      if (response.data.success) {
        alert(`License activated successfully! Your tier is now ${response.data.tier.toUpperCase()}.`);
        setLicenseKeyInput('');
        setShowLicenseInput(false);
        setLicensePreview(null);
        await fetchLicenseStatus();
        // Refresh subscription tier
        try {
          const response = await axios.get(`${API_URL}/api/v1/stripe/status`);
          setSubscriptionTier(response.data.subscription_tier || 'free');
        } catch (err: any) {
          logger.error('Failed to refresh subscription status:', err);
        }
      } else {
        throw new Error(response.data.error || 'Activation failed');
      }
    } catch (err: any) {
      logger.error('Failed to activate license:', err);
      const errorMessage = err.response?.data?.detail?.error || err.response?.data?.detail?.message || err.response?.data?.error || err.message || 'Failed to activate license';
      alert(`License activation failed: ${errorMessage}`);
    } finally {
      setActivatingLicense(false);
    }
  };

  const getTierDisplayName = (tier: string) => {
    const tierMap: Record<string, string> = {
      'community': 'Community',
      'starter': 'Starter',
      'pro': 'Pro',
      'msp': 'MSP',
      'standard': 'Community', // Legacy
      'enterprise': 'MSP' // Legacy
    };
    return tierMap[tier?.toLowerCase()] || tier?.toUpperCase() || 'Community';
  };

  const getTierColor = (tier: string) => {
    const tierMap: Record<string, string> = {
      'community': 'gray',
      'starter': 'blue',
      'pro': 'purple',
      'msp': 'green'
    };
    return tierMap[tier?.toLowerCase()] || 'gray';
  };

  const updateSetting = async (key: keyof SettingsState, value: boolean) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);

    // Update tenant settings via API (tenant-wide)
    try {
      const apiKey = key === 'showDevTroubleshooting' ? 'show_dev_troubleshooting' : 'enable_debug_logs';
      await axios.put(`${API_URL}/api/v1/tenants/current/settings`, {
        [apiKey]: value
      });

      // Update sessionStorage for logger
      if (key === 'enableDebugLogs') {
        sessionStorage.setItem('tenant_enable_debug_logs', value.toString());
      }

      // Trigger a custom event so other components can react to settings changes
      window.dispatchEvent(new CustomEvent('settingsChanged', { detail: newSettings }));
    } catch (err: any) {
      logger.error('Failed to update tenant settings:', err);
      // Revert on error
      setSettings(settings);
      alert('Failed to update settings. Please try again.');
    }
  };

  // Save RackPlane Services API Key
  const saveRackplaneApiKey = async () => {
    if (!rackplaneApiKeyInput.trim()) {
      alert('Please enter an API key');
      return;
    }

    setSavingApiKey(true);
    try {
      // Use axios defaults (already set by AuthContext) - don't manually add headers
      const response = await axios.put(`${API_URL}/api/v1/tenants/current/settings`, {
        rackplane_api_key: rackplaneApiKeyInput.trim()
      });

      // The PUT endpoint returns the updated settings, use that directly
      if (response.data) {
        setRackplaneApiKeyConfigured(response.data.rackplane_api_key_configured || false);
        setRackplaneApiKeyPreview(response.data.rackplane_api_key_preview || null);
        setRackplaneCloudConnected(response.data.rackplane_cloud_connected || false);
      } else {
        // Fallback: refresh settings if response doesn't have expected structure
        const refreshResponse = await axios.get(`${API_URL}/api/v1/tenants/current/settings`);
        setRackplaneApiKeyConfigured(refreshResponse.data.rackplane_api_key_configured || false);
        setRackplaneApiKeyPreview(refreshResponse.data.rackplane_api_key_preview || null);
        setRackplaneCloudConnected(refreshResponse.data.rackplane_cloud_connected || false);
      }

      setRackplaneApiKeyInput('');
      setShowApiKeyInput(false);
      alert('RackPlane Services API key saved successfully!');
    } catch (err: any) {
      logger.error('Failed to save RackPlane API key:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to save API key. Please try again.';
      alert(`Unable to add key: ${errorMessage}`);
    } finally {
      setSavingApiKey(false);
    }
  };
  const requestContributorAccess = async () => {
    if (!agreeToTerms) {
      alert("You must agree to the terms to join the Contributor Program.");
      return;
    }

    setRequestingAccess(true);
    try {
      await axios.post(`${API_URL}/api/v1/contributor/request-access`, {
        contributor_agreement: true
      });
      setContributorProgramEnrolled(true);
      alert("Access request submitted! Your application is pending review. You will receive an email once approved.");
    } catch (error: any) {
      logger.error('Error requesting contributor access:', error);
      alert("Failed to submit request. Please try again.");
    } finally {
      setRequestingAccess(false);
    }
  };

  const removeRackplaneApiKey = async () => {
    if (!window.confirm('Are you sure you want to remove your RackPlane Services API key? This will disable access to the Global SKU Catalog.')) {
      return;
    }

    setSavingApiKey(true);
    try {
      // Use axios defaults (already set by AuthContext) - don't manually add headers
      const response = await axios.put(`${API_URL}/api/v1/tenants/current/settings`, {
        rackplane_api_key: ''
      });

      // Update state from response
      if (response.data) {
        setRackplaneApiKeyConfigured(response.data.rackplane_api_key_configured || false);
        setRackplaneApiKeyPreview(response.data.rackplane_api_key_preview || null);
        setRackplaneCloudConnected(response.data.rackplane_cloud_connected || false);
      } else {
        setRackplaneApiKeyConfigured(false);
        setRackplaneApiKeyPreview(null);
        setRackplaneCloudConnected(false);
      }

      alert('RackPlane Services API key removed.');
    } catch (err: any) {
      logger.error('Failed to remove RackPlane API key:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to remove API key. Please try again.';
      alert(`Failed to remove API key: ${errorMessage}`);
    } finally {
      setSavingApiKey(false);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-3xl font-bold text-primary">Settings</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Configure application preferences</p>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-1 overflow-x-auto" aria-label="Settings tabs">
          {settingsTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${activeTab === tab.id
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* License & Subscription Section */}
      {(activeTab === 'all' || activeTab === 'license') && (
        <div className="card mb-6 animate-fade-in">
          <h2 className="text-xl font-bold text-primary mb-4">License & Subscription</h2>

          {loadingLicense ? (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">Loading license status...</div>
          ) : (
            <div className="space-y-4">
              {/* Current License Status */}
              {licenseStatus && (
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--bg-light)' }}>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold text-white bg-${getTierColor(licenseStatus.tier)}-600`}>
                          {getTierDisplayName(licenseStatus.tier)}
                        </span>
                        {licenseStatus.license_type && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            ({licenseStatus.license_type.toUpperCase()})
                          </span>
                        )}
                      </div>
                      {licenseStatus.activated_at && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Activated: {new Date(licenseStatus.activated_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    {licenseStatus.seats && (
                      <div className="text-right">
                        <div className="text-sm font-medium text-primary">
                          {licenseStatus.seats_used || 0} / {licenseStatus.seats === -1 ? '∞' : licenseStatus.seats} seats
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">Users</div>
                      </div>
                    )}
                  </div>

                  {/* Expiration Warning */}
                  {licenseStatus.license_warning && (
                    <div className={`mb-4 p-3 rounded-lg ${licenseStatus.days_until_expiry !== null && licenseStatus.days_until_expiry < 0
                      ? 'bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800'
                      : licenseStatus.days_until_expiry !== null && licenseStatus.days_until_expiry <= 7
                        ? 'bg-yellow-100 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-800'
                        : 'bg-blue-100 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-800'
                      }`}>
                      <div className="flex items-start gap-2">
                        <span className="text-lg">
                          {licenseStatus.days_until_expiry !== null && licenseStatus.days_until_expiry < 0 ? '⚠️' : 'ℹ️'}
                        </span>
                        <div className="flex-1">
                          <p className={`text-sm font-medium ${licenseStatus.days_until_expiry !== null && licenseStatus.days_until_expiry < 0
                            ? 'text-red-800 dark:text-red-200'
                            : licenseStatus.days_until_expiry !== null && licenseStatus.days_until_expiry <= 7
                              ? 'text-yellow-800 dark:text-yellow-200'
                              : 'text-blue-800 dark:text-blue-200'
                            }`}>
                            {licenseStatus.license_warning}
                          </p>
                          {licenseStatus.expires_at && (
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                              Expires: {new Date(licenseStatus.expires_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Enabled Features */}
                  {licenseStatus.features && Object.keys(licenseStatus.features).length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium text-primary mb-2">Enabled Features</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(licenseStatus.features)
                          .filter(([key, value]) => {
                            if (key === '_metadata') return false;
                            if (value === true) return true;
                            if (typeof value === 'object' && value !== null && 'enabled' in value) {
                              return (value as any).enabled === true;
                            }
                            return false;
                          })
                          .map(([key]) => (
                            <span
                              key={key}
                              className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 text-xs rounded"
                            >
                              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </span>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* License Activation - Gated for OSS */}
              {!isOss ? (
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--bg-light)' }}>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-medium text-primary">Activate License</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Enter your license key (JWT token or API key) to upgrade your subscription tier
                      </p>
                    </div>
                    {!showLicenseInput && (
                      <button
                        onClick={() => setShowLicenseInput(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                      >
                        Enter License Key
                      </button>
                    )}
                  </div>

                  {showLicenseInput && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">License Key</label>
                        <textarea
                          value={licenseKeyInput}
                          onChange={(e) => setLicenseKeyInput(e.target.value)}
                          placeholder="Enter your license key (JWT token or API key starting with rp_ or rk_)"
                          rows={3}
                          className="input-field w-full font-mono text-sm"
                        />
                      </div>

                      {/* License Preview */}
                      {licensePreview && licensePreview.valid && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                          <div className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">
                            Preview: {getTierDisplayName(licensePreview.tier)} License
                          </div>
                          {licensePreview.seats && (
                            <div className="text-xs text-blue-700 dark:text-blue-300">
                              Seats: {licensePreview.seats === -1 ? 'Unlimited' : licensePreview.seats}
                            </div>
                          )}
                          {licensePreview.expires_at && (
                            <div className="text-xs text-blue-700 dark:text-blue-300">
                              Expires: {new Date(licensePreview.expires_at).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <button
                          onClick={validateLicensePreview}
                          disabled={validatingLicense || !licenseKeyInput.trim()}
                          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm disabled:opacity-50"
                        >
                          {validatingLicense ? 'Validating...' : 'Preview'}
                        </button>
                        <button
                          onClick={activateLicense}
                          disabled={activatingLicense || !licenseKeyInput.trim()}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
                        >
                          {activatingLicense ? 'Activating...' : 'Activate License'}
                        </button>
                        <button
                          onClick={() => {
                            setShowLicenseInput(false);
                            setLicenseKeyInput('');
                            setLicensePreview(null);
                          }}
                          className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="card mb-6 border-2 border-dashed border-gray-300 dark:border-gray-600 mt-4">
                  <div className="text-center py-8">
                    <div className="text-4xl mb-2">💎</div>
                    <h2 className="text-xl font-bold text-primary mb-2">Upgrade to Premium</h2>
                    <p className="text-gray-500 dark:text-gray-400 mb-4">
                      Unlock multi-tenancy, white-labeling, and advanced integrations.
                    </p>
                    <a
                      href="https://rackplane.com/pricing"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
                    >
                      View Pricing
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* UI Preferences - General Tab */}
      {(activeTab === 'all' || activeTab === 'general') && (
        <div className="card mb-6 animate-fade-in">
          <h2 className="text-xl font-bold text-primary mb-4">UI Preferences</h2>


          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div>
                <h3 className="font-medium text-primary">Developer Troubleshooting</h3>
                <p className="text-xs text-muted-foreground">
                  Show detailed error messages and stack traces in the UI.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.showDevTroubleshooting}
                  onChange={(e) => updateSetting('showDevTroubleshooting', e.target.checked)}
                  disabled={loadingSettings}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 peer-disabled:opacity-50"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div>
                <h3 className="font-medium text-primary">Debug Logs</h3>
                <p className="text-xs text-muted-foreground">
                  Enable verbose logging in the browser console.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableDebugLogs}
                  onChange={(e) => updateSetting('enableDebugLogs', e.target.checked)}
                  disabled={loadingSettings}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 peer-disabled:opacity-50"></div>
              </label>
            </div>
          </div>
        </div>
      )
      }

      {/* RackPlane Cloud Services Section - Integrations Tab */}
      {
        (activeTab === 'all' || activeTab === 'integrations') && (
          <>
            {!isOss ? (
              <div className="card mb-6 animate-fade-in">
                <h2 className="text-xl font-bold text-primary mb-2">RackPlane Cloud Services</h2>

                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                  <strong>Join the Global Intelligence Network.</strong> Connect your instance to unlock Cloud OCR, Auto-Warranty, and the Visual SKU Database.
                </p>

                {/* FS.com Integration Status - Premium feature, hidden until useful */}
                {/* FS.com Integration Status - Premium feature, hidden until useful */}
                <FeatureGate feature="vendor_apis" fallback={null}>
                  <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4">
                    <h3 className="text-sm font-bold text-primary flex items-center gap-2 mb-3">
                      <span className="text-blue-600">🔌</span> FS.com API Integration
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                          Connect to FS.com for real-time stock, pricing, and order imports.
                          API limits are enforced by FS.com.
                        </p>
                        <div className="flex items-center gap-2 text-sm">
                          Status:
                          {fsRateLimits ? (
                            <span className="text-green-600 font-medium">Connected</span>
                          ) : (
                            <span className="text-gray-500">Not detected / credentials missing</span>
                          )}
                        </div>
                      </div>

                      {fsRateLimits && (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold text-gray-500 uppercase">Rate Limits</div>

                          <div className="flex justify-between items-center text-sm">
                            <span>Hourly Limit</span>
                            <span className="font-mono">
                              {fsRateLimits.hourly.used} / {fsRateLimits.hourly.limit}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                            <div
                              className={`h-1.5 rounded-full ${fsRateLimits.hourly.remaining === 0 ? 'bg-red-600' : 'bg-blue-600'}`}
                              style={{ width: `${Math.min(100, (fsRateLimits.hourly.used / fsRateLimits.hourly.limit) * 100)}%` }}
                            ></div>
                          </div>

                          <div className="flex justify-between items-center text-sm">
                            <span>Daily Limit</span>
                            <span className="font-mono">
                              {fsRateLimits.daily.used} / {fsRateLimits.daily.limit}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                            <div
                              className={`h-1.5 rounded-full ${fsRateLimits.daily.remaining === 0 ? 'bg-red-600' : 'bg-green-600'}`}
                              style={{ width: `${Math.min(100, (fsRateLimits.daily.used / fsRateLimits.daily.limit) * 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </FeatureGate>

                {/* Amazon Business Punchout Integration */}
                <div className="p-4 rounded-lg border mb-4" style={{ backgroundColor: 'var(--bg-light)' }}>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-sm font-bold text-primary flex items-center gap-2">
                        <span>🛒</span> Amazon Business Punchout
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Enable one-click procurement from Amazon Business. Users can shop on Amazon and return items to their RackPlane cart.
                      </p>
                    </div>
                  </div>

                  <AmazonPunchoutConfig />
                </div>

                {/* Contributor Program - Hidden until implemented */}
                {SHOW_CONTRIBUTOR_PROGRAM && (
                  <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 mb-4">
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="text-sm font-bold text-purple-800 dark:text-purple-200 flex items-center gap-2">
                        <span>🤝</span> The Contributor Program (Bounties & Rewards)
                      </h3>
                      {contributorProgramEnrolled && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 text-xs rounded-full font-bold border border-purple-200 dark:border-purple-700">
                          ACTIVE CONTRIBUTOR
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-700 dark:text-gray-300 mb-3">
                      We believe the community builds the best data. We pay you in credits to help us build it.
                    </p>

                    <div className="space-y-2 text-xs mb-4">
                      <div className="flex items-start gap-2">
                        <span className="text-green-600 font-bold">✓</span>
                        <div>
                          <strong className="text-primary">The "Fair Trade" Rule:</strong>
                          <span className="text-gray-600 dark:text-gray-400"> If Cloud OCR doesn't recognize your item, and you manually add the correct data (Model, Specs, Image), that scan is free. We never charge you for doing our work.</span>
                        </div>
                      </div>
                      <div className="flex items-start gap-2">
                        <span className="text-green-600 font-bold">✓</span>
                        <div>
                          <strong className="text-primary">Earn Bounties:</strong>
                          <span className="text-gray-600 dark:text-gray-400"> Submit your manual entry to the Global Database. If verified, you earn <strong className="text-purple-600 dark:text-purple-400">50 Cloud OCR Credits</strong>.</span>
                        </div>
                      </div>
                      {!contributorProgramEnrolled && (
                        <>
                          <div className="flex items-start gap-2">
                            <span className="text-green-600 font-bold">✓</span>
                            <div>
                              <strong className="text-primary">The Math:</strong>
                              <span className="text-gray-600 dark:text-gray-400"> Submit just 10 new items, and you earn <strong className="text-purple-600 dark:text-purple-400">500 Free Scans</strong>.</span>
                            </div>
                          </div>
                          <div className="flex items-start gap-2">
                            <span className="text-green-600 font-bold">✓</span>
                            <div>
                              <strong className="text-primary">Unlock Premium:</strong>
                              <span className="text-gray-600 dark:text-gray-400"> Use your earned credits to access Rich Media lookups (Images, Thermal, Power data) even on the Community plan.</span>
                            </div>
                          </div>
                        </>
                      )}
                    </div>

                    {!contributorProgramEnrolled ? (
                      <div className="mt-4 pt-3 border-t border-purple-200 dark:border-purple-800">
                        <label className="flex items-start gap-2 cursor-pointer mb-3">
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={agreeToTerms}
                            onChange={(e) => setAgreeToTerms(e.target.checked)}
                          />
                          <span className="text-xs text-gray-600 dark:text-gray-400">
                            I agree to the <strong>Fair Trade Rule</strong>. I understand that submitting false or low-quality data (spam) to the Global Database will result in a permanent ban from the Contributor Program and revocation of all earned credits.
                          </span>
                        </label>
                        <button
                          onClick={requestContributorAccess}
                          disabled={requestingAccess || !agreeToTerms}
                          className="w-full py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg text-sm font-bold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          {requestingAccess ? "Joining..." : "Join Contributor Program"}
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3 p-3 bg-white dark:bg-gray-800 rounded border border-purple-100 dark:border-purple-900/50">
                        <div className="flex items-center justify-between">
                          <div className="text-xs text-gray-500">Current Balance</div>
                          <div className="text-sm font-bold text-purple-600 dark:text-purple-400">0 Credits</div>
                        </div>
                        <div className="text-xs text-gray-400 mt-1 italic">
                          Start defining items to earn credits.
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Privacy & Control */}
                <div className="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-3 mb-4">
                  <h4 className="text-xs font-bold text-primary mb-2">🔒 Privacy & Control</h4>
                  <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                    <p>
                      <strong className="text-primary">You are in control:</strong> Data is only shared when you explicitly click "Submit to Global" on a specific asset.
                    </p>
                    <p>
                      <strong className="text-primary">Zero Leakage:</strong> Your private inventory counts, locations, and IP addresses never leave your server. We only care about the hardware definition (e.g., "What does a Dell R740 look like?").
                    </p>
                  </div>
                </div>

                {/* Status & Actions */}
                <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-light)' }}>
                  {rackplaneApiKeyConfigured ? (
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          {rackplaneCloudConnected ? (
                            <>
                              <span className="text-green-500">🟢</span>
                              <span className="text-sm font-medium text-primary">Connected to RackPlane Cloud</span>
                            </>
                          ) : (
                            <>
                              <span className="text-yellow-500">🟡</span>
                              <span className="text-sm font-medium text-primary">Key Configured (Not Connected)</span>
                            </>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground font-mono">
                          {rackplaneApiKeyPreview || 'rk_****...****'}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setShowApiKeyInput(true)}
                          className="px-3 py-1.5 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded"
                        >
                          Update Key
                        </button>
                        <button
                          onClick={removeRackplaneApiKey}
                          disabled={savingApiKey}
                          className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
                        >
                          Disconnect
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <span>🟡</span>
                        <span className="text-sm font-medium text-primary">No API Key Configured</span>
                      </div>
                      <div className="flex gap-3">
                        <a
                          href="mailto:support@rackplane.com?subject=Request%20Free%20API%20Key&body=Please%20provide%20a%20RackPlane%20Cloud%20API%20key%20for%20my%20instance."
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                        >
                          Request Free API Key
                        </a>
                        <button
                          onClick={() => setShowApiKeyInput(true)}
                          className="px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 text-primary rounded-lg text-sm"
                        >
                          Enter Key
                        </button>
                      </div>
                    </div>
                  )}

                  {showApiKeyInput && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <label className="block text-sm font-medium text-primary mb-2">Enter API Key</label>
                      <div className="flex gap-2">
                        <input
                          type="password"
                          value={rackplaneApiKeyInput}
                          onChange={(e) => setRackplaneApiKeyInput(e.target.value)}
                          placeholder="rk_live_..."
                          className="input-field flex-1"
                        />
                        <button
                          onClick={saveRackplaneApiKey}
                          disabled={savingApiKey || !rackplaneApiKeyInput.trim()}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:opacity-50"
                        >
                          {savingApiKey ? 'Saving...' : 'Connect'}
                        </button>
                        <button
                          onClick={() => {
                            setShowApiKeyInput(false);
                            setRackplaneApiKeyInput('');
                          }}
                          className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg"
                        >
                          Cancel
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        Your API key will be stored securely and only a masked preview will be shown.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="card mb-6 border-2 border-dashed border-gray-300 dark:border-gray-600">
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">☁️</div>
                  <h2 className="text-xl font-bold text-primary mb-2">RackPlane Cloud Services</h2>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    Amazon Business Punchout, Cloud OCR, and Global Intelligence Network.
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Upgrade to Premium to unlock cloud services.
                  </p>
                  <a
                    href="https://rackplane.com/pricing"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
                  >
                    View Plans
                  </a>
                </div>
              </div>
            )}
          </>
        )
      }

      {/* Remote Printers Section - Printers Tab, Paid tiers only */}
      {
        (activeTab === 'all' || activeTab === 'printers') && (
          <div className="animate-fade-in">
            {isPaidTier ? (
              <div className="card mb-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-primary">Remote Printers</h2>
                  <button
                    onClick={generateApiKey}
                    disabled={generating}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generating ? 'Generating...' : '+ Add Printer'}
                  </button>
                </div>

                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Configure remote label printers using the RackPlane Print Agent. Each printer needs its own API key.
                  Keys are prefixed with "rp_" and can be revoked at any time.
                </p>

                {/* Add Printer Form */}
                <div className="mb-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Printer Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., 'Warehouse Label Printer' or 'Lab-1 Brother QL-820NWB'"
                      value={newKeyLabel}
                      onChange={(e) => setNewKeyLabel(e.target.value)}
                      className="input"
                      style={{ maxWidth: '400px' }}
                    />
                  </div>

                  {/* Scope Selection */}
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Permissions (Scopes)
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                      Select which functions this API key can access. Leave "All Scopes" checked for full access.
                    </p>

                    <div className="space-y-2 mb-3">
                      <label className="flex items-start p-3 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-subtle-card cursor-pointer">
                        <input
                          type="checkbox"
                          checked={useAllScopes}
                          onChange={(e) => handleAllScopesToggle(e.target.checked)}
                          className="mt-1 mr-3"
                        />
                        <div>
                          <div className="font-medium text-primary">All Scopes (Full Access)</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">Access to all API endpoints. Recommended for general use.</div>
                        </div>
                      </label>
                    </div>

                    {!useAllScopes && (
                      <div className="space-y-2 border-t border-gray-300 dark:border-gray-600 pt-3">
                        <div className="text-xs font-medium text-primary mb-2">Or select specific scopes:</div>
                        {availableScopes.map((scope) => (
                          <label key={scope.value} className="flex items-start p-3 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-subtle-card cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedScopes.includes(scope.value)}
                              onChange={() => handleScopeToggle(scope.value)}
                              className="mt-1 mr-3"
                            />
                            <div className="flex-1">
                              <div className="font-medium text-primary">{scope.label}</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">{scope.description}</div>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Configured Printers List */}
                {loadingKeys ? (
                  <div className="text-center py-4 text-gray-500 dark:text-gray-400">Loading...</div>
                ) : apiKeys.length === 0 ? (
                  <div className="text-center py-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
                    <div className="text-4xl mb-2">🖨️</div>
                    <p className="text-gray-500 dark:text-gray-400 mb-2">No remote printers configured</p>
                    <p className="text-sm text-gray-400 dark:text-gray-500">Click "+ Add Printer" to configure your first remote label printer.</p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-sm font-medium text-primary mb-3">Configured Printers ({apiKeys.length})</h3>
                    <div className="space-y-3">
                      {apiKeys.map((key) => (
                        <div key={key.id} className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-card">
                          <div className="flex items-center gap-4">
                            <div className="text-2xl">🖨️</div>
                            <div>
                              <div className="font-medium text-primary">{key.label || 'Unlabeled Printer'}</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                Added {formatDate(key.created_at)} • Last used: {formatDate(key.last_used_at)}
                              </div>
                              {key.scopes && key.scopes.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {key.scopes.map((scope) => (
                                    <span key={scope} className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded">
                                      {scope}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${key.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                              }`}>
                              {key.is_active ? 'Active' : 'Revoked'}
                            </span>
                            <button
                              onClick={() => revokeApiKey(key.id)}
                              disabled={!key.is_active}
                              className="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Upgrade prompt for free tier */
              <div className="card mb-6 border-2 border-dashed border-gray-300 dark:border-gray-600">
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">🖨️</div>
                  <h2 className="text-xl font-bold text-primary mb-2">Remote Printers</h2>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    Configure remote label printers for your warehouse, lab, or datacenter.
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Upgrade to Starter or higher to use remote printers.
                  </p>
                  <a
                    href="/subscription"
                    className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
                  >
                    View Plans
                  </a>
                </div>
              </div>
            )}
            {showKeyModal && newKey && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-card rounded-lg shadow-xl p-6 max-w-2xl w-full mx-4">
                  <h3 className="text-xl font-bold text-primary mb-4">⚠️ Save Your API Key</h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    This is the only time you'll see this key. Copy it now and store it securely!
                  </p>
                  <div className="bg-subtle-card p-4 rounded mb-4">
                    <code className="text-sm break-all text-primary">{newKey}</code>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyToClipboard(newKey)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                    >
                      Copy to Clipboard
                    </button>
                    <button
                      onClick={() => {
                        setShowKeyModal(false);
                        setNewKey(null);
                      }}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg"
                    >
                      I've Saved It
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      }

      {/* Info Section - Show only on All tab */}
      {
        activeTab === 'all' && (
          <div className="card border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
            <h3 className="font-bold mb-2 text-blue-900 dark:text-blue-300">ℹ️ About Settings</h3>
            <ul className="list-disc list-inside text-sm space-y-1 text-blue-800 dark:text-blue-300">
              <li>Settings are saved at the tenant level (applies to all users in your organization)</li>
              <li>Only tenant administrators can modify these settings</li>
              <li>Changes take effect immediately for all users in your tenant</li>
              <li>Settings persist across all devices and browsers for your tenant</li>
            </ul>
          </div>
        )
      }
    </div >
  );
};

export default Settings;

