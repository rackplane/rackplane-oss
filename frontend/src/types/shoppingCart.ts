
export interface CartItem {
    id: number;
    quantity: number;
    unit_price?: number;
    notes?: string;
    sku_details?: Record<string, any>;
    catalog_sku_id?: number;
    vendor_sku_id?: number;
    vendor_sku?: {
        name: string;
        vendor: string;
        sku: string;
        manufacturer?: string;
        asset_type?: string;
        image_url?: string;
    };
}

export interface ShoppingCart {
    id: number;
    name: string;
    notes?: string;
    items: CartItem[];
    total_items: number;
    total_cost?: number;
    created_at: string;
    updated_at?: string;
}

export interface CartItemCreate {
    catalog_sku_id?: number;
    vendor_sku_id?: number;
    quantity?: number;
    notes?: string;
}

export interface ShoppingCartCreate {
    name: string;
    notes?: string;
}
