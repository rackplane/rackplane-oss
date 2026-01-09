import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useCart } from '../contexts/CartContext';
import { API_URL } from '../config/api';

interface OrderResult {
    success: boolean;
    order_id: string;
    amazon_confirmation?: string;
    message: string;
}

interface PunchoutStatus {
    enabled: boolean;
    configured: boolean;
    mode: 'test' | 'production';
}

const Checkout: React.FC = () => {
    const { cart, clearCart } = useCart();
    const [orderPlaced, setOrderPlaced] = useState(false);
    const [orderResult, setOrderResult] = useState<OrderResult | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [punchoutStatus, setPunchoutStatus] = useState<PunchoutStatus | null>(null);

    // Fetch punchout status to know test vs production mode
    useEffect(() => {
        const fetchPunchoutStatus = async () => {
            try {
                const response = await axios.get(`${API_URL}/api/v1/punchout/amazon/status`);
                setPunchoutStatus(response.data);
            } catch (err) {
                // Ignore errors - just means punchout isn't configured
            }
        };
        fetchPunchoutStatus();
    }, []);

    const isTestMode = punchoutStatus?.mode === 'test';

    const subtotal = cart?.items.reduce(
        (sum, item) => sum + (item.unit_price || 0) * item.quantity,
        0
    ) || 0;

    // Check if cart contains Amazon Business items
    const hasAmazonItems = cart?.items.some(
        (item) => item.vendor_sku?.vendor === 'Amazon Business'
    ) || false;

    const amazonItemCount = cart?.items.filter(
        (item) => item.vendor_sku?.vendor === 'Amazon Business'
    ).length || 0;

    const handlePlaceOrder = async () => {

        if (!cart) return;

        setError(null);
        setIsSubmitting(true);

        try {
            if (hasAmazonItems) {
                // Submit to Amazon Business
                const response = await axios.post<OrderResult>(
                    `${API_URL}/api/v1/punchout/amazon/order`,
                    { cart_id: cart.id }
                );
                setOrderResult(response.data);
            }

            // Clear cart after successful submission
            await clearCart();
            setOrderPlaced(true);
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.data?.detail) {
                setError(err.response.data.detail);
            } else {
                setError('Failed to submit order. Please try again.');
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    if (orderPlaced) {
        return (
            <div className="max-w-2xl mx-auto py-16 text-center">
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-8">
                    <svg
                        className="w-16 h-16 text-green-500 mx-auto mb-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <h1 className="text-2xl font-bold text-green-700 dark:text-green-300 mb-2">
                        {orderResult ? 'Order Submitted to Amazon Business!' : 'Order Placed Successfully!'}
                    </h1>
                    {orderResult ? (
                        <div className="text-gray-600 dark:text-gray-400 mb-6">
                            <p className="mb-2">Order ID: <span className="font-mono font-semibold">{orderResult.order_id}</span></p>
                            <p className="text-sm">
                                {orderResult.message}
                            </p>
                            <p className="text-sm mt-2 text-yellow-600 dark:text-yellow-400">
                                The order will go through Amazon's approval workflow before being fulfilled.
                            </p>
                        </div>
                    ) : (
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            Thank you for your order.
                        </p>
                    )}
                    <Link
                        to="/"
                        className="inline-block px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primary-hover transition"
                    >
                        Return to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    if (!cart || cart.items.length === 0) {
        return (
            <div className="max-w-2xl mx-auto py-16 text-center">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-8">
                    <svg
                        className="w-16 h-16 text-gray-400 mx-auto mb-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
                        />
                    </svg>
                    <h1 className="text-xl font-bold text-gray-700 dark:text-gray-300 mb-2">
                        Your Cart is Empty
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mb-6">
                        Add some items to your cart before checking out.
                    </p>
                    <Link
                        to="/vendor-skus"
                        className="inline-block px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primary-hover transition"
                    >
                        Browse Products
                    </Link>
                </div>
            </div>
        );
    }



    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Checkout</h1>

            {/* Amazon Business Badge */}
            {hasAmazonItems && (
                <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 mb-6">
                    <div className="flex items-center">
                        <svg className="w-6 h-6 text-orange-500 mr-3" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15l-5-5 1.41-1.41L11 14.17l7.59-7.59L20 8l-9 9z" />
                        </svg>
                        <div>
                            <p className="text-sm font-medium text-orange-700 dark:text-orange-300">
                                Amazon Business Order ({amazonItemCount} item{amazonItemCount > 1 ? 's' : ''})
                            </p>
                            <p className="text-xs text-orange-600 dark:text-orange-400">
                                This order will be submitted to Amazon Business for approval and fulfillment.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Error Alert */}
            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
                    <div className="flex items-start">
                        <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div>
                            <p className="text-sm font-medium text-red-700 dark:text-red-300">Order Failed</p>
                            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Cart Items */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden mb-6">
                <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                Item
                            </th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                Qty
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                Price
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                Subtotal
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {cart.items.map((item) => (
                            <tr key={item.id}>
                                <td className="px-6 py-4">
                                    <div className="flex items-center">
                                        {item.vendor_sku?.vendor === 'Amazon Business' && (
                                            <span className="inline-block w-2 h-2 bg-orange-500 rounded-full mr-2" title="Amazon Business" />
                                        )}
                                        <div>
                                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                {item.vendor_sku?.name || `Item #${item.id}`}
                                            </div>
                                            <div className="text-sm text-gray-500 dark:text-gray-400">
                                                {item.vendor_sku?.vendor || item.vendor_sku?.manufacturer || 'Unknown'}
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-center text-sm text-gray-900 dark:text-white">
                                    {item.quantity}
                                </td>
                                <td className="px-6 py-4 text-right text-sm text-gray-900 dark:text-white">
                                    ${(item.unit_price || 0).toFixed(2)}
                                </td>
                                <td className="px-6 py-4 text-right text-sm font-medium text-gray-900 dark:text-white">
                                    ${((item.unit_price || 0) * item.quantity).toFixed(2)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Order Summary */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Order Summary</h2>
                <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>Subtotal ({cart.total_items} items)</span>
                    <span>${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>Shipping</span>
                    <span className="text-green-600">Calculated at fulfillment</span>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 mt-4 pt-4">
                    <div className="flex justify-between text-lg font-bold text-gray-900 dark:text-white">
                        <span>Total</span>
                        <span>${subtotal.toFixed(2)}</span>
                    </div>
                </div>
            </div>

            {/* Info Notice */}
            {hasAmazonItems ? (
                <div className={`${isTestMode ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800' : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'} border rounded-lg p-4 mb-6`}>
                    <div className="flex items-start">
                        <svg className={`w-5 h-5 ${isTestMode ? 'text-yellow-500' : 'text-blue-500'} mt-0.5 mr-3`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div>
                            <p className={`text-sm ${isTestMode ? 'text-yellow-700 dark:text-yellow-300' : 'text-blue-700 dark:text-blue-300'} font-medium`}>
                                Amazon Business Purchase {isTestMode && <span className="ml-2 px-2 py-0.5 bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200 rounded text-xs">TEST MODE</span>}
                            </p>
                            <p className={`text-sm ${isTestMode ? 'text-yellow-600 dark:text-yellow-400' : 'text-blue-600 dark:text-blue-400'}`}>
                                {isTestMode ? (
                                    <>Clicking "Submit to Amazon" will send this order to Amazon's <strong>test environment</strong>. No real order will be placed.</>
                                ) : (
                                    <>Clicking "Submit to Amazon" will send this order to Amazon Business. It will go through your organization's approval workflow before being fulfilled.</>
                                )}
                            </p>
                            <p className={`text-xs ${isTestMode ? 'text-yellow-500' : 'text-blue-500'} mt-1`}>
                                Your cart will be cleared after successful submission.
                            </p>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
                    <div className="flex items-start">
                        <svg className="w-5 h-5 text-yellow-500 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div>
                            <p className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">Demo Mode</p>
                            <p className="text-sm text-yellow-600 dark:text-yellow-400">
                                This cart does not contain Amazon Business items. Use Amazon Punchout to shop and add items for purchasing.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-4">
                <div className="flex gap-4">
                    <button
                        onClick={handlePlaceOrder}
                        disabled={isSubmitting || !cart || cart.items.length === 0}
                        className={`flex-1 px-6 py-3 font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed ${hasAmazonItems
                            ? 'bg-orange-600 hover:bg-orange-700 text-white'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                            }`}
                    >
                        {isSubmitting ? 'Submitting...' : hasAmazonItems ? (isTestMode ? 'Submit to Amazon (Test)' : 'Submit to Amazon Business') : 'Place Order'}
                    </button>
                    <Link
                        to="/"
                        className="px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition text-center"
                    >
                        Continue Shopping
                    </Link>
                </div>
                {hasAmazonItems && (
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            <strong>Note:</strong> Amazon Business orders require Purchase Order/Invoice access on your Amazon account.
                            If order submission fails, contact your Amazon Business administrator.
                        </p>
                    </div>
                )}

            </div>
        </div>
    );
};

export default Checkout;
