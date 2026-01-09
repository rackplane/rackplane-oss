from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime
from app.api.v1.vendor_skus import VendorSKUResponse

# Constants (mirrored from model for validation)
MAX_ITEM_QUANTITY = 10000


class CartItemCreate(BaseModel):
    """Schema for creating a cart item."""
    catalog_sku_id: Optional[int] = None
    vendor_sku_id: Optional[int] = None
    quantity: int = 1
    notes: Optional[str] = None

    @model_validator(mode='after')
    def validate_at_least_one_sku(self) -> 'CartItemCreate':
        """Ensure at least one SKU ID is provided."""
        if self.catalog_sku_id is None and self.vendor_sku_id is None:
            raise ValueError('Must provide either catalog_sku_id or vendor_sku_id')
        return self

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Ensure quantity is within valid range."""
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        if v > MAX_ITEM_QUANTITY:
            raise ValueError(f'Quantity cannot exceed {MAX_ITEM_QUANTITY}')
        return v


class CartItemResponse(BaseModel):
    """Schema for cart item in API responses."""
    id: int
    quantity: int
    unit_price: Optional[float] = None
    notes: Optional[str] = None
    catalog_sku_id: Optional[int] = None
    vendor_sku_id: Optional[int] = None
    vendor_sku: Optional[VendorSKUResponse] = None
    # catalog_sku: Optional[CatalogSKUResponse] = None  # Add if needed

    class Config:
        from_attributes = True


class ShoppingCartCreate(BaseModel):
    """Schema for creating a shopping cart."""
    name: str = "My Cart"
    notes: Optional[str] = None


class ShoppingCartUpdate(BaseModel):
    """Schema for updating a shopping cart."""
    name: Optional[str] = None
    notes: Optional[str] = None


class ShoppingCartResponse(BaseModel):
    """Schema for shopping cart in API responses."""
    id: int
    name: str
    notes: Optional[str]
    items: List[CartItemResponse]
    total_items: int = 0
    total_cost: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
