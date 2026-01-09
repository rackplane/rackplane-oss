"""
Shopping Cart Service

Handles shopping cart operations with proper concurrency control.

Concurrency Safety:
    All cart modification operations (add_item, remove_item, update_item_quantity)
    use SELECT...FOR UPDATE to prevent race conditions:

    - add_item: Prevents duplicate cart items when adding same SKU concurrently
    - update_item_quantity: Prevents lost updates when modifying quantity concurrently
    - remove_item: Prevents errors when removing same item concurrently

    PostgreSQL Note:
        FOR UPDATE doesn't work with LEFT OUTER JOINs, so we use noload() to disable
        eager loading of relationships (catalog_sku, vendor_sku) during lock acquisition.

    See tests/test_shopping_cart_concurrency_pytest.py for concurrency test coverage.
"""

from sqlalchemy.orm import Session, noload
from typing import Optional, List
from fastapi import HTTPException, status
import logging

from app.models.shopping_cart import ShoppingCart, CartItem
from app.models.catalog_sku import CatalogSKU
from app.models.vendor_sku import VendorSKU
from app.schemas.shopping_cart import ShoppingCartCreate, CartItemCreate

logger = logging.getLogger(__name__)

class ShoppingCartService:
    def __init__(self, db: Session):
        self.db = db

    def get_cart_by_id(self, cart_id: int, tenant_id: int) -> Optional[ShoppingCart]:
        logger.debug(f"get_cart_by_id id={cart_id} tenant={tenant_id}")
        return self.db.query(ShoppingCart).filter(
            ShoppingCart.id == cart_id,
            ShoppingCart.tenant_id == tenant_id
        ).first()

    def get_cart_for_user(self, cart_id: int, tenant_id: int, user_id: int) -> Optional[ShoppingCart]:
        """Get cart with atomic authorization check.

        Authorization is performed atomically via database query to prevent TOCTOU races.

        Returns:
            ShoppingCart if found and user authorized, None if not found or not authorized
        """
        return self.db.query(ShoppingCart).filter(
            ShoppingCart.id == cart_id,
            ShoppingCart.tenant_id == tenant_id,
            ShoppingCart.user_id == user_id
        ).first()

    def get_user_carts(self, user_id: int, tenant_id: int) -> List[ShoppingCart]:
        return self.db.query(ShoppingCart).filter(
            ShoppingCart.user_id == user_id,
            ShoppingCart.tenant_id == tenant_id,
            ShoppingCart.is_active == True
        ).all()
    
    def create_cart(self, user_id: int, tenant_id: int, schema: ShoppingCartCreate) -> ShoppingCart:
        cart = ShoppingCart(
            name=schema.name,
            user_id=user_id,
            tenant_id=tenant_id,
            notes=schema.notes,
            is_active=True
        )
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def delete_cart(self, cart_id: int, tenant_id: int, user_id: int) -> bool:
        """Delete a shopping cart with proper authorization.

        Raises:
            HTTPException: 403 if user not authorized to delete cart

        Returns:
            True if cart was deleted, False if cart not found
        """
        try:
            # Lock cart for deletion
            # Include user_id in filter to prevent unauthorized users from acquiring locks (DOS prevention)
            cart = self.db.query(ShoppingCart).options(
                noload(ShoppingCart.items)
            ).filter(
                ShoppingCart.id == cart_id,
                ShoppingCart.tenant_id == tenant_id,
                ShoppingCart.user_id == user_id
            ).with_for_update().first()

            if not cart:
                return False

            # Items are deleted via cascade
            self.db.delete(cart)
            self.db.commit()
            return True
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting cart: {e}")
            raise

    def add_item(self, cart_id: int, schema: CartItemCreate, tenant_id: int, user_id: int) -> CartItem:
        """Add item to cart with proper concurrency control.

        Raises:
            HTTPException: 404 if cart or SKU not found
            HTTPException: 403 if user not authorized to modify cart
            HTTPException: 400 if neither catalog_sku_id nor vendor_sku_id provided
        """
        try:
            # CRITICAL: Lock ShoppingCart FIRST to prevent deadlocks
            # All methods must lock in same order: ShoppingCart -> CartItem
            # Use noload() to prevent eager loading of relationships (LEFT OUTER JOIN incompatible with FOR UPDATE)
            # Include user_id in filter to prevent unauthorized users from acquiring locks (DOS prevention)
            cart = self.db.query(ShoppingCart).options(
                noload(ShoppingCart.items)
            ).filter(
                ShoppingCart.id == cart_id,
                ShoppingCart.tenant_id == tenant_id,
                ShoppingCart.user_id == user_id
            ).with_for_update().first()

            if not cart:
                # Return 404 for both "not found" and "unauthorized" to prevent user enumeration
                # (attacker cannot distinguish "cart doesn't exist" from "access denied")
                raise HTTPException(status_code=404, detail="Shopping cart not found")

            # Check validation of SKU existence
            sku = None  # Initialize to satisfy type checker
            if schema.catalog_sku_id:
                logger.debug(f"Looking for CatalogSKU id={schema.catalog_sku_id}")
                sku = self.db.query(CatalogSKU).filter(CatalogSKU.id == schema.catalog_sku_id).first()
                if not sku:
                    logger.debug(f"Catalog SKU {schema.catalog_sku_id} NOT FOUND")
                    raise HTTPException(status_code=404, detail="Catalog SKU not found")
            elif schema.vendor_sku_id:
                logger.debug(f"Looking for VendorSKU id={schema.vendor_sku_id}")
                sku = self.db.query(VendorSKU).filter(
                    VendorSKU.id == schema.vendor_sku_id,
                    VendorSKU.tenant_id == tenant_id
                ).first()
                if not sku:
                    logger.debug(f"Vendor SKU {schema.vendor_sku_id} NOT FOUND")
                    raise HTTPException(status_code=404, detail="Vendor SKU not found")
            else:
                raise HTTPException(status_code=400, detail="Must provide catalog_sku_id or vendor_sku_id")

            # Check if item exists in cart (same SKU) - use FOR UPDATE to prevent race conditions
            # Note: We must disable eager loading (lazy="joined") relationships to avoid LEFT OUTER JOINs
            # PostgreSQL doesn't allow FOR UPDATE on queries with outer joins
            query = self.db.query(CartItem).options(
                noload(CartItem.catalog_sku),
                noload(CartItem.vendor_sku)
            ).filter(
                CartItem.cart_id == cart_id,
                CartItem.tenant_id == tenant_id
            )
            if schema.catalog_sku_id:
                query = query.filter(CartItem.catalog_sku_id == schema.catalog_sku_id)
            if schema.vendor_sku_id:
                query = query.filter(CartItem.vendor_sku_id == schema.vendor_sku_id)

            # Lock the row to prevent concurrent updates creating duplicates
            existing_item = query.with_for_update().first()

            if existing_item:
                existing_item.quantity += schema.quantity
                if schema.notes:
                    existing_item.notes = schema.notes
                # updated_at is handled by onupdate=func.now() in the model
                self.db.commit()
                self.db.refresh(existing_item)
                return existing_item


            # New Item
            unit_price = getattr(sku, 'price_usd', None)
            new_item = CartItem(
                cart_id=cart_id,
                tenant_id=tenant_id,
                catalog_sku_id=schema.catalog_sku_id,
                vendor_sku_id=schema.vendor_sku_id,
                quantity=schema.quantity,
                unit_price=unit_price,
                notes=schema.notes
            )
            self.db.add(new_item)
            self.db.commit()
            self.db.refresh(new_item)
            return new_item
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding item to cart: {e}")
            raise

    def remove_item(self, cart_id: int, item_id: int, tenant_id: int, user_id: int) -> bool:
        """Remove item from cart with proper concurrency control.

        Raises:
            HTTPException: 403 if user not authorized to modify cart

        Returns:
            True if item was removed, False if item not found
        """
        try:
            # CRITICAL: Lock ShoppingCart FIRST to prevent deadlocks
            # Use noload() to prevent eager loading of relationships (LEFT OUTER JOIN incompatible with FOR UPDATE)
            # Include user_id in filter to prevent unauthorized users from acquiring locks (DOS prevention)
            cart = self.db.query(ShoppingCart).options(
                noload(ShoppingCart.items)
            ).filter(
                ShoppingCart.id == cart_id,
                ShoppingCart.tenant_id == tenant_id,
                ShoppingCart.user_id == user_id
            ).with_for_update().first()

            if not cart:
                return False

            # Then lock CartItem
            item = self.db.query(CartItem).options(
                noload(CartItem.catalog_sku),
                noload(CartItem.vendor_sku)
            ).filter(
                CartItem.id == item_id,
                CartItem.cart_id == cart_id,
                CartItem.tenant_id == tenant_id
            ).with_for_update().first()

            if not item:
                return False

            self.db.delete(item)
            self.db.commit()
            return True
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing item from cart: {e}")
            raise

    def update_item_quantity(self, cart_id: int, item_id: int, quantity: int, tenant_id: int, user_id: int) -> Optional[CartItem]:
        """Update cart item quantity with proper concurrency control.

        Raises:
            HTTPException: 403 if user not authorized to modify cart

        Returns:
            Updated CartItem if quantity > 0, None if item deleted or not found
        """
        try:
            # CRITICAL: Lock ShoppingCart FIRST to prevent deadlocks
            # Use noload() to prevent eager loading of relationships (LEFT OUTER JOIN incompatible with FOR UPDATE)
            # Include user_id in filter to prevent unauthorized users from acquiring locks (DOS prevention)
            cart = self.db.query(ShoppingCart).options(
                noload(ShoppingCart.items)
            ).filter(
                ShoppingCart.id == cart_id,
                ShoppingCart.tenant_id == tenant_id,
                ShoppingCart.user_id == user_id
            ).with_for_update().first()

            if not cart:
                return None

            # Then lock CartItem
            item = self.db.query(CartItem).options(
                noload(CartItem.catalog_sku),
                noload(CartItem.vendor_sku)
            ).filter(
                CartItem.id == item_id,
                CartItem.cart_id == cart_id,
                CartItem.tenant_id == tenant_id
            ).with_for_update().first()

            if not item:
                return None

            if quantity <= 0:
                self.db.delete(item)
                self.db.commit()
                return None

            item.quantity = quantity
            # updated_at is handled by onupdate=func.now() in the model
            self.db.commit()
            self.db.refresh(item)
            return item
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating item quantity: {e}")
            raise
