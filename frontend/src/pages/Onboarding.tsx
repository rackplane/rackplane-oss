// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import logger from '../utils/logger';

const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    company_name: '',
    company_slug: '',
    contact_email: '',
    contact_phone: '',
    admin_username: '',
    admin_password: '',
    admin_password_confirm: '',
    admin_email: '',
    subscription_tier: 'standard'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.company_name.trim()) {
      newErrors.company_name = 'Company name is required';
    }

    if (!formData.admin_username.trim()) {
      newErrors.admin_username = 'Admin username is required';
    } else if (formData.admin_username.length < 3) {
      newErrors.admin_username = 'Username must be at least 3 characters';
    }

    if (!formData.admin_password) {
      newErrors.admin_password = 'Password is required';
    } else if (formData.admin_password.length < 6) {
      newErrors.admin_password = 'Password must be at least 6 characters';
    }

    if (formData.admin_password !== formData.admin_password_confirm) {
      newErrors.admin_password_confirm = 'Passwords do not match';
    }

    if (formData.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email)) {
      newErrors.contact_email = 'Invalid email format';
    }

    if (formData.admin_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.admin_email)) {
      newErrors.admin_email = 'Invalid email format';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Prepare request payload (exclude password_confirm)
      const payload = {
        company_name: formData.company_name.trim(),
        company_slug: formData.company_slug.trim() || undefined,
        contact_email: formData.contact_email.trim() || undefined,
        contact_phone: formData.contact_phone.trim() || undefined,
        admin_username: formData.admin_username.trim(),
        admin_password: formData.admin_password,
        admin_email: formData.admin_email.trim() || undefined,
        subscription_tier: formData.subscription_tier
      };

      const response = await axios.post(`${API_URL}/api/v1/tenants/onboard`, payload);

      // Store the token from onboarding response
      if (response.data.access_token) {
        localStorage.setItem('auth_token', response.data.access_token);
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;

        // Update auth context by logging in with the new credentials
        // This ensures the auth state is properly set
        await login(formData.admin_username, formData.admin_password);
      }

      // Redirect to dashboard
      navigate('/');
    } catch (error: any) {
      logger.error('Onboarding failed:', error);
      if (error.response?.data?.detail) {
        setSubmitError(error.response.data.detail);
      } else {
        setSubmitError('Failed to create tenant. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-card rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-primary mb-2">Welcome to DCMS</h1>
            <p className="text-gray-500 dark:text-gray-400">Set up your organization to get started</p>
          </div>

          {submitError && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{submitError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Company Information */}
            <div className="border-b border-gray-200 pb-6">
              <h2 className="text-xl font-semibold text-primary mb-4">Company Information</h2>

              <div className="mb-4">
                <label htmlFor="company_name" className="block text-sm font-medium text-primary mb-1">
                  Company Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="company_name"
                  name="company_name"
                  value={formData.company_name}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.company_name ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="Acme Corporation"
                />
                {errors.company_name && (
                  <p className="mt-1 text-sm text-red-600">{errors.company_name}</p>
                )}
              </div>

              <div className="mb-4">
                <label htmlFor="company_slug" className="block text-sm font-medium text-primary mb-1">
                  Company Slug (Optional)
                </label>
                <input
                  type="text"
                  id="company_slug"
                  name="company_slug"
                  value={formData.company_slug}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="acme-corporation (auto-generated if empty)"
                  pattern="[a-z0-9-]+"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">URL-friendly identifier (lowercase, hyphens only)</p>
              </div>

              <div className="mb-4">
                <label htmlFor="contact_email" className="block text-sm font-medium text-primary mb-1">
                  Contact Email (Optional)
                </label>
                <input
                  type="email"
                  id="contact_email"
                  name="contact_email"
                  value={formData.contact_email}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.contact_email ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="contact@acme.com"
                />
                {errors.contact_email && (
                  <p className="mt-1 text-sm text-red-600">{errors.contact_email}</p>
                )}
              </div>

              <div className="mb-4">
                <label htmlFor="contact_phone" className="block text-sm font-medium text-primary mb-1">
                  Contact Phone (Optional)
                </label>
                <input
                  type="tel"
                  id="contact_phone"
                  name="contact_phone"
                  value={formData.contact_phone}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div>
                <label htmlFor="subscription_tier" className="block text-sm font-medium text-primary mb-1">
                  Subscription Tier
                </label>
                <select
                  id="subscription_tier"
                  name="subscription_tier"
                  value={formData.subscription_tier}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
            </div>

            {/* Admin User Information */}
            <div className="border-b border-gray-200 pb-6">
              <h2 className="text-xl font-semibold text-primary mb-4">Admin Account</h2>

              <div className="mb-4">
                <label htmlFor="admin_username" className="block text-sm font-medium text-primary mb-1">
                  Username <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="admin_username"
                  name="admin_username"
                  value={formData.admin_username}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.admin_username ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="admin"
                />
                {errors.admin_username && (
                  <p className="mt-1 text-sm text-red-600">{errors.admin_username}</p>
                )}
              </div>

              <div className="mb-4">
                <label htmlFor="admin_password" className="block text-sm font-medium text-primary mb-1">
                  Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="admin_password"
                  name="admin_password"
                  value={formData.admin_password}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.admin_password ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="Minimum 6 characters"
                />
                {errors.admin_password && (
                  <p className="mt-1 text-sm text-red-600">{errors.admin_password}</p>
                )}
              </div>

              <div className="mb-4">
                <label htmlFor="admin_password_confirm" className="block text-sm font-medium text-primary mb-1">
                  Confirm Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="admin_password_confirm"
                  name="admin_password_confirm"
                  value={formData.admin_password_confirm}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.admin_password_confirm ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="Re-enter password"
                />
                {errors.admin_password_confirm && (
                  <p className="mt-1 text-sm text-red-600">{errors.admin_password_confirm}</p>
                )}
              </div>

              <div>
                <label htmlFor="admin_email" className="block text-sm font-medium text-primary mb-1">
                  Admin Email (Optional)
                </label>
                <input
                  type="email"
                  id="admin_email"
                  name="admin_email"
                  value={formData.admin_email}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.admin_email ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="admin@acme.com"
                />
                {errors.admin_email && (
                  <p className="mt-1 text-sm text-red-600">{errors.admin_email}</p>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="px-6 py-2 border border-default rounded-lg text-primary hover:bg-table-row-hover transition"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Creating...' : 'Create Account'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Onboarding;

