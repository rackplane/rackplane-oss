from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, DateTime, Float, Index, CheckConstraint, func
from sqlalchemy.orm import relationship, Mapped

from app.core.database import Base
from app.core.tenant_mixin import TenantMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.catalog_sku import CatalogSKU
    from app.models.vendor_sku import VendorSKU

# Constants
DEFAULT_CART_NAME = "My Cart"
MAX_ITEM_QUANTITY = 10000

class ShoppingCart(Base, TenantMixin):
    """Named shopping cart belonging to a user."""
    __tablename__ = "shopping_carts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, default=DEFAULT_CART_NAME)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    # Use server-side timestamps to avoid datetime.utcnow() deprecation
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships with type hints for IDE support
    user: Mapped["User"] = relationship("User", backref="shopping_carts")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", 
        back_populates="cart", 
        cascade="all, delete-orphan",
        lazy="joined"  # Eager load to prevent N+1 queries
    )
    
    @property
    def total_items(self) -> int:
        """Total number of items in the cart."""
        return sum(item.quantity for item in self.items)
    
    @property
    def total_cost(self) -> float:
        """Total cost of all items in the cart."""
        return sum(
            (item.unit_price or 0) * item.quantity 
            for item in self.items
        )


class CartItem(Base, TenantMixin):
    """Individual item in a shopping cart."""
    __tablename__ = "cart_items"
    __table_args__ = (
        Index('ix_cart_items_cart_id', 'cart_id'),
        # Composite index for efficient SKU lookups
        Index('ix_cart_items_cart_sku', 'cart_id', 'vendor_sku_id', 'catalog_sku_id'),
        # Ensure at least one SKU reference is provided
        CheckConstraint(
            'catalog_sku_id IS NOT NULL OR vendor_sku_id IS NOT NULL',
            name='ck_cart_items_at_least_one_sku'
        ),
        # Ensure quantity is within valid range
        CheckConstraint(
            f'quantity >= 1 AND quantity <= {MAX_ITEM_QUANTITY}',
            name='ck_cart_items_quantity_range'
        ),
    )
    
    id = Column(Integer, primary_key=True)
    # CASCADE: When cart is deleted, delete items too
    cart_id = Column(Integer, ForeignKey("shopping_carts.id", ondelete="CASCADE"), nullable=False)
    
    # Reference to SKU (at least one must be provided - enforced by CHECK constraint)
    # SET NULL: When SKU is deleted, set reference to NULL (item remains in cart with null ref)
    catalog_sku_id = Column(Integer, ForeignKey("catalog_skus.id", ondelete="SET NULL"), nullable=True)
    vendor_sku_id = Column(Integer, ForeignKey("vendor_skus.id", ondelete="SET NULL"), nullable=True)
    
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=True)  # Snapshot price at time of adding
    notes = Column(Text, nullable=True)
    
    # Use server-side timestamps to avoid datetime.utcnow() deprecation
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships with type hints
    cart: Mapped["ShoppingCart"] = relationship("ShoppingCart", back_populates="items")
    catalog_sku: Mapped["CatalogSKU | None"] = relationship("CatalogSKU", lazy="joined")
    vendor_sku: Mapped["VendorSKU | None"] = relationship("VendorSKU", lazy="joined")
