// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import logger from '../utils/logger';

interface PortDefinition {
    port_number: string;
    port_type: string;
    speed_mbps?: number;
    duplex?: string;
    poe_capable?: boolean;
    poe_max_watts?: number;
}

interface PortTemplate {
    id: number;
    manufacturer: string;
    model: string;
    description?: string;
    port_definitions: PortDefinition[];
    created_at?: string;
}

interface TemplateSelectorProps {
    assetId: number;
    onApply: () => void;
}

const TemplateSelector: React.FC<TemplateSelectorProps> = ({ assetId, onApply }) => {
    const [templates, setTemplates] = useState<PortTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [applying, setApplying] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
    const [overwrite, setOverwrite] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        fetchTemplates();
    }, []);

    const fetchTemplates = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_URL}/api/v1/port-templates/`);
            setTemplates(response.data || []);
        } catch (err: any) {
            logger.error('Error fetching templates:', err);
            setError('Failed to load templates');
        } finally {
            setLoading(false);
        }
    };

    const handleApply = async () => {
        if (!selectedTemplate) {
            alert('Please select a template');
            return;
        }

        try {
            setApplying(true);
            setError(null);

            const response = await axios.post(`${API_URL}/api/v1/port-templates/apply`, {
                asset_id: assetId,
                template_id: selectedTemplate,
                overwrite: overwrite
            });

            alert(`Successfully created ${response.data.ports_created} ports!`);
            setSelectedTemplate(null);
            setOverwrite(false);
            setExpanded(false);
            onApply();
        } catch (err: any) {
            logger.error('Error applying template:', err);
            const message = err.response?.data?.detail || err.message;
            if (message.includes('already has')) {
                setError('Device already has ports. Check "Replace existing" to overwrite.');
            } else {
                setError('Failed to apply template: ' + message);
            }
        } finally {
            setApplying(false);
        }
    };

    const selectedTemplateData = templates.find(t => t.id === selectedTemplate);

    if (loading) {
        return (
            <div className="text-sm text-gray-500">Loading templates...</div>
        );
    }

    return (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center justify-between w-full text-left"
            >
                <span className="font-medium text-primary">
                    📋 Apply Port Template
                </span>
                <span className="text-gray-400">{expanded ? '▼' : '▶'}</span>
            </button>

            {expanded && (
                <div className="mt-4 space-y-4">
                    {templates.length === 0 ? (
                        <p className="text-sm text-gray-500">
                            No templates available. {' '}
                            <Link to="/port-templates" className="text-blue-600 hover:underline">
                                Create templates in the Port Templates page
                            </Link>.
                        </p>
                    ) : (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">
                                    Select Template
                                </label>
                                <select
                                    value={selectedTemplate || ''}
                                    onChange={(e) => setSelectedTemplate(e.target.value ? parseInt(e.target.value) : null)}
                                    className="input w-full"
                                >
                                    <option value="">-- Choose a template --</option>
                                    {templates.map((template) => (
                                        <option key={template.id} value={template.id}>
                                            {template.manufacturer} {template.model} ({template.port_definitions.length} ports)
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {selectedTemplateData && (
                                <div className="bg-white dark:bg-gray-700 rounded p-3 text-sm">
                                    <div className="font-medium text-primary mb-1">
                                        {selectedTemplateData.manufacturer} {selectedTemplateData.model}
                                    </div>
                                    {selectedTemplateData.description && (
                                        <p className="text-gray-500 text-xs mb-2">{selectedTemplateData.description}</p>
                                    )}
                                    <p className="text-gray-600 dark:text-gray-300">
                                        <strong>{selectedTemplateData.port_definitions.length}</strong> ports will be created
                                    </p>
                                    <div className="mt-2 flex flex-wrap gap-1">
                                        {selectedTemplateData.port_definitions.slice(0, 5).map((def, i) => (
                                            <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                                                {def.port_number}: {def.port_type}
                                            </span>
                                        ))}
                                        {selectedTemplateData.port_definitions.length > 5 && (
                                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                                                +{selectedTemplateData.port_definitions.length - 5} more
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="overwrite"
                                    checked={overwrite}
                                    onChange={(e) => setOverwrite(e.target.checked)}
                                    className="rounded"
                                />
                                <label htmlFor="overwrite" className="text-sm text-gray-600 dark:text-gray-300">
                                    Replace existing ports
                                </label>
                            </div>

                            {error && (
                                <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                                    {error}
                                </div>
                            )}

                            <button
                                onClick={handleApply}
                                disabled={!selectedTemplate || applying}
                                className="btn-primary w-full disabled:opacity-50"
                            >
                                {applying ? 'Applying...' : 'Apply Template'}
                            </button>

                            <div className="text-center">
                                <Link
                                    to="/port-templates"
                                    className="text-xs text-blue-500 hover:underline"
                                >
                                    ⚙️ Manage Port Templates
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default TemplateSelector;
