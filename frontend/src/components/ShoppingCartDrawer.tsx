
import React from 'react';
import { useCart } from '../contexts/CartContext';
import { Link } from 'react-router-dom';
import { CartItem } from '../types/shoppingCart';

const ShoppingCartDrawer: React.FC = () => {
    const { isOpen, cart, toggleCart, removeFromCart, updateQuantity, isLoading } = useCart();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 overflow-hidden">
            <div className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={toggleCart}></div>

            <div className="fixed inset-y-0 right-0 max-w-full flex">
                <div className="w-screen max-w-md">
                    <div className="h-full flex flex-col bg-white dark:bg-gray-800 shadow-xl overflow-y-scroll">
                        <div className="flex-1 py-6 overflow-y-auto px-4 sm:px-6">
                            <div className="flex items-start justify-between">
                                <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">Shopping Cart</h2>
                                <div className="ml-3 h-7 flex items-center">
                                    <button
                                        onClick={toggleCart}
                                        className="bg-white dark:bg-gray-800 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                    >
                                        <span className="sr-only">Close panel</span>
                                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            <div className="mt-8">
                                <div className="flow-root">
                                    {!cart || cart.items.length === 0 ? (
                                        <div className="text-center py-10">
                                            <p className="text-gray-500 dark:text-gray-400">Your cart is empty.</p>
                                            <button
                                                onClick={toggleCart}
                                                className="mt-4 text-indigo-600 hover:text-indigo-500 font-medium"
                                            >
                                                Continue Shopping
                                            </button>
                                        </div>
                                    ) : (
                                        <ul className="-my-6 divide-y divide-gray-200 dark:divide-gray-700">
                                            {cart.items.map((item: CartItem) => (
                                                <li key={item.id} className="py-6 flex">
                                                    <div className="flex-shrink-0 w-24 h-24 border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden bg-gray-50 flex items-center justify-center">
                                                        {item.vendor_sku?.image_url ? (
                                                            <img
                                                                src={item.vendor_sku.image_url}
                                                                alt={item.vendor_sku.name}
                                                                className="h-full w-full object-contain p-1"
                                                                onError={(e) => {
                                                                    const target = e.target as HTMLImageElement;
                                                                    target.style.display = 'none';
                                                                    target.nextElementSibling?.classList.remove('hidden');
                                                                }}
                                                            />
                                                        ) : null}
                                                        <svg
                                                            className={`h-10 w-10 text-gray-400 ${item.vendor_sku?.image_url ? 'hidden' : ''}`}
                                                            fill="none"
                                                            viewBox="0 0 24 24"
                                                            stroke="currentColor"
                                                            aria-label="Product image placeholder"
                                                            role="img"
                                                        >
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                        </svg>
                                                    </div>

                                                    <div className="ml-4 flex-1 flex flex-col">
                                                        <div>
                                                            <div className="flex justify-between text-base font-medium text-gray-900 dark:text-white">
                                                                <h3>
                                                                    {item.vendor_sku?.name || `Item #${item.id}`}
                                                                </h3>
                                                                <p className="ml-4">
                                                                    {item.unit_price ? `$${item.unit_price.toFixed(2)}` : '$-'}
                                                                </p>
                                                            </div>
                                                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                                                {item.vendor_sku?.vendor || item.vendor_sku?.manufacturer || 'Unknown Vendor'}
                                                            </p>
                                                        </div>
                                                        <div className="flex-1 flex items-end justify-between text-sm">
                                                            <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded">
                                                                <button
                                                                    onClick={() => updateQuantity(item.id, item.quantity - 1)}
                                                                    className="px-2 py-1 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                                                    disabled={isLoading}
                                                                >
                                                                    -
                                                                </button>
                                                                <span className="px-2 text-gray-900 dark:text-white">{item.quantity}</span>
                                                                <button
                                                                    onClick={() => updateQuantity(item.id, item.quantity + 1)}
                                                                    className="px-2 py-1 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                                                    disabled={isLoading}
                                                                >
                                                                    +
                                                                </button>
                                                            </div>

                                                            <div className="flex">
                                                                <button
                                                                    type="button"
                                                                    onClick={() => removeFromCart(item.id)}
                                                                    className="font-medium text-red-600 hover:text-red-500"
                                                                    disabled={isLoading}
                                                                >
                                                                    Remove
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>
                        </div>

                        {cart && cart.items.length > 0 && (
                            <div className="border-t border-gray-200 dark:border-gray-700 py-6 px-4 sm:px-6">
                                <div className="flex justify-between text-base font-medium text-gray-900 dark:text-white">
                                    <p>Subtotal</p>
                                    <p>${cart.items.reduce((sum, item) => sum + (item.unit_price || 0) * item.quantity, 0).toFixed(2)}</p>
                                </div>
                                <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Shipping and taxes calculated at checkout.</p>
                                <div className="mt-6">
                                    <Link
                                        to="/checkout"
                                        className="flex justify-center items-center px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                                        onClick={toggleCart}
                                    >
                                        Checkout
                                    </Link>
                                </div>
                                <div className="mt-6 flex justify-center text-sm text-center text-gray-500 dark:text-gray-400">
                                    <p>
                                        or{' '}
                                        <button
                                            type="button"
                                            className="text-indigo-600 font-medium hover:text-indigo-500"
                                            onClick={toggleCart}
                                        >
                                            Continue Shopping<span aria-hidden="true"> &rarr;</span>
                                        </button>
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShoppingCartDrawer;
