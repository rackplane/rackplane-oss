// Asset-related type definitions
// Extracted from Assets.tsx for reusability

export interface Asset {
    id: number;
    asset_tag: string;
    serial_number: string;
    asset_type: string;
    manufacturer: string;
    model: string;
    status: string;
    on_loan?: boolean;
    loan_direction?: string;
    loan_party?: string;
    loan_source?: string;
    hostname?: string;
    height_u?: number;
    power_consumption_watts?: number;
    description?: string;
    datacenter_id?: number;
    rack_id?: number;
    rack_position_start?: number;
    rack_position_end?: number;
    storage_container_id?: number;
    storage_location?: string;
    container_id?: number;
    min_stock_threshold?: number;
    purchase_cost?: number;
    purchase_date?: string;
    currency?: string;
    supplier?: string;
    warranty_start_date?: string;
    warranty_end_date?: string;
    connector_type_end_a?: string;
    connector_type_end_b?: string;
    custom_fields?: {
        cable_length?: string;
        connector_type?: string;
        quantity?: number;
        fiber_type?: string;
        fiber_connector_a?: string;
        fiber_connector_b?: string;
        fiber_breakout?: string;
        dac_speed?: string;
        dac_connector_a?: string;
        dac_connector_b?: string;
        dac_breakout?: string;
        ethernet_category?: string;
        [key: string]: any;
    };
    cable_length?: string;
    connector_type?: string;
    quantity?: number;
}

export interface AssetFormData {
    asset_tag: string;
    serial_number: string;
    asset_type: string;
    manufacturer: string;
    model: string;
    status: string;
    on_loan: boolean;
    loan_direction: string;
    loan_party: string;
    loan_source: string;
    hostname: string;
    height_u: string;
    power_consumption_watts: string;
    description: string;
    sku: string;
    datacenter_id: string;
    rack_id: string;
    rack_position_start: string;
    storage_container_id: string;
    storage_location: string;
    container_id: string;
    min_stock_threshold: string;
    purchase_cost: string;
    purchase_date: string;
    currency: string;
    supplier: string;
    po_number: string;
    warranty_start_date: string;
    warranty_end_date: string;
    cable_length: string;
    connector_type: string;
    quantity: string;
    fiber_type: string;
    fiber_connector_a: string;
    fiber_connector_b: string;
    fiber_breakout: string;
    dac_speed: string;
    dac_connector_a: string;
    dac_connector_b: string;
    dac_breakout: string;
    ethernet_category: string;
}

export interface AssetType {
    id: number;
    name: string;
    display_name: string;
    is_active: boolean;
    features?: Record<string, any>;
}

export interface Datacenter {
    id: number;
    name: string;
    code: string;
}

export interface Rack {
    id: number;
    name: string;
    datacenter_id: number;
}

export interface StorageContainer {
    id: number;
    name: string;
    container_type: string;
    location?: string;
    room_id?: number;
    datacenter_id?: number;
}

export interface Room {
    id: number;
    name: string;
    code: string;
    datacenter_id: number;
}

export interface PortDefinition {
    port_number: string;
    port_type: string;
    speed_mbps?: number;
    duplex?: string;
    poe_capable?: boolean;
    poe_max_watts?: number;
}

export interface PortTemplate {
    id: number;
    manufacturer: string;
    model: string;
    description?: string;
    port_definitions: PortDefinition[];
}

// Default form data for creating new assets
export const DEFAULT_ASSET_FORM_DATA: AssetFormData = {
    asset_tag: '',
    serial_number: '',
    asset_type: '',
    manufacturer: '',
    model: '',
    status: 'received',
    on_loan: false,
    loan_direction: 'to_us',
    loan_party: '',
    loan_source: '',
    hostname: '',
    height_u: '',
    power_consumption_watts: '',
    description: '',
    sku: '',
    datacenter_id: '',
    rack_id: '',
    rack_position_start: '',
    storage_container_id: '',
    storage_location: '',
    container_id: '',
    min_stock_threshold: '',
    purchase_cost: '',
    purchase_date: '',
    currency: 'USD',
    supplier: '',
    po_number: '',
    warranty_start_date: '',
    warranty_end_date: '',
    cable_length: '',
    connector_type: '',
    quantity: '',
    fiber_type: '',
    fiber_connector_a: '',
    fiber_connector_b: '',
    fiber_breakout: '',
    dac_speed: '',
    dac_connector_a: '',
    dac_connector_b: '',
    dac_breakout: '',
    ethernet_category: '',
};
