
import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from './AuthContext';
import logger from '../utils/logger';
import { ShoppingCart, CartItemCreate } from '../types/shoppingCart';

interface CartContextType {
    cart: ShoppingCart | null;
    isLoading: boolean;
    isOpen: boolean;
    toggleCart: () => void;
    createCart: (name?: string) => Promise<void>;
    addToCart: (item: CartItemCreate) => Promise<void>;
    updateQuantity: (itemId: number, quantity: number) => Promise<void>;
    removeFromCart: (itemId: number) => Promise<void>;
    clearCart: () => Promise<void>;
    refreshCart: () => Promise<void>;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const useCart = () => {
    const context = useContext(CartContext);
    if (!context) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
};

interface CartProviderProps {
    children: ReactNode;
}

export const CartProvider: React.FC<CartProviderProps> = ({ children }) => {
    const { isAuthenticated } = useAuth();
    const [cart, setCart] = useState<ShoppingCart | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    const fetchCart = useCallback(async () => {
        if (!isAuthenticated) return;

        try {
            setIsLoading(true);
            // Get all carts for user. For now, we just pick the first one or create one if none exist.
            const response = await axios.get(`${API_URL}/api/v1/shopping-carts/`);
            const carts: ShoppingCart[] = response.data;

            if (carts.length > 0) {
                // Use the first cart (most recently created or default)
                // Ideally we might check for an 'active' flag or 'last_updated'
                setCart(carts[0]);
            } else {
                setCart(null);
            }
        } catch (error) {
            logger.error('Failed to fetch shopping cart', error);
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated]);

    useEffect(() => {
        if (isAuthenticated) {
            fetchCart();
        } else {
            setCart(null);
        }
    }, [isAuthenticated, fetchCart]);

    const toggleCart = () => {
        logger.debug('Toggling cart, current state:', isOpen);
        setIsOpen(!isOpen);
    };

    const createCart = async (name: string = "My Cart") => {
        try {
            setIsLoading(true);
            const response = await axios.post(`${API_URL}/api/v1/shopping-carts/`, { name });
            setCart(response.data);
        } catch (error) {
            logger.error('Failed to create cart', error);
            throw error;
        } finally {
            setIsLoading(false);
        }
    };

    const getOrCreateCartId = async (): Promise<number> => {
        if (cart) return cart.id;

        // Create new cart
        const response = await axios.post(`${API_URL}/api/v1/shopping-carts/`, { name: "My Cart" });
        setCart(response.data);
        return response.data.id;
    };

    const addToCart = async (item: CartItemCreate) => {
        try {
            const cartId = await getOrCreateCartId();
            await axios.post(`${API_URL}/api/v1/shopping-carts/${cartId}/items`, item);
            await refreshCart(); // Refresh to get updated total/list
            setIsOpen(true); // Open cart when adding item
        } catch (error) {
            logger.error('Failed to add item to cart', error);
            throw error;
        }
    };

    const updateQuantity = async (itemId: number, quantity: number) => {
        if (!cart) return;
        try {
            if (quantity <= 0) {
                await removeFromCart(itemId);
                return;
            }
            await axios.put(`${API_URL}/api/v1/shopping-carts/${cart.id}/items/${itemId}`, null, {
                params: { quantity }
            });
            await refreshCart();
        } catch (error) {
            logger.error('Failed to update item quantity', error);
            throw error;
        }
    };

    const removeFromCart = async (itemId: number) => {
        if (!cart) return;
        try {
            await axios.delete(`${API_URL}/api/v1/shopping-carts/${cart.id}/items/${itemId}`);
            await refreshCart();
        } catch (error) {
            logger.error('Failed to remove item from cart', error);
            throw error;
        }
    };

    const refreshCart = async () => {
        if (!cart) {
            await fetchCart();
            return;
        }
        try {
            // Fetch specific cart to get latest details
            const response = await axios.get(`${API_URL}/api/v1/shopping-carts/${cart.id}`);
            setCart(response.data);
        } catch (error) {
            logger.error('Failed to refresh cart', error);
            // Fallback to fetch all
            await fetchCart();
        }
    };

    const clearCart = async () => {
        if (!cart) return;
        try {
            setIsLoading(true);
            await axios.delete(`${API_URL}/api/v1/shopping-carts/${cart.id}`);
            setCart(null);
        } catch (error) {
            logger.error('Failed to clear cart', error);
            throw error;
        } finally {
            setIsLoading(false);
        }
    };

    const value = {
        cart,
        isLoading,
        isOpen,
        toggleCart,
        createCart,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        refreshCart
    };

    return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};
