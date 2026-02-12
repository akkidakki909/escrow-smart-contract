'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, getUser, clearAuth } from '@/lib/api';

interface MenuItem {
    id: number;
    name: string;
    price: number;
    category: string;
    emoji: string;
}

interface CartItem extends MenuItem {
    qty: number;
}

interface BillItem {
    name: string;
    emoji: string;
    qty: number;
    unit_price: number;
    line_total: number;
}

interface Bill {
    order_id: number;
    student_id: number;
    vendor: string;
    items: BillItem[];
    total: number;
    txn_id: string;
    timestamp: string;
    payment_method: string;
}

interface Order {
    id: number;
    total: number;
    txn_id: string;
    status: string;
    time: string;
    items: { name: string; emoji: string; qty: number; price: number }[];
}

export default function CanteenPage() {
    const router = useRouter();
    const [menu, setMenu] = useState<MenuItem[]>([]);
    const [cart, setCart] = useState<CartItem[]>([]);
    const [orders, setOrders] = useState<Order[]>([]);
    const [bill, setBill] = useState<Bill | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState<'menu' | 'orders'>('menu');
    const [balance, setBalance] = useState(0);

    useEffect(() => {
        const user = getUser();
        if (!user || user.role !== 'student') {
            router.push('/');
            return;
        }
        loadMenu();
        loadBalance();
        loadOrders();
    }, []);

    const loadMenu = async () => {
        try {
            const res = await api('/canteen/menu');
            setMenu(res.items);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const loadBalance = async () => {
        try {
            const res = await api('/student/balance');
            setBalance(res.balance);
        } catch { }
    };

    const loadOrders = async () => {
        try {
            const res = await api('/canteen/orders');
            setOrders(res.orders);
        } catch { }
    };

    const addToCart = (item: MenuItem) => {
        setCart(prev => {
            const existing = prev.find(c => c.id === item.id);
            if (existing) {
                return prev.map(c => c.id === item.id ? { ...c, qty: c.qty + 1 } : c);
            }
            return [...prev, { ...item, qty: 1 }];
        });
    };

    const removeFromCart = (itemId: number) => {
        setCart(prev => {
            const existing = prev.find(c => c.id === itemId);
            if (existing && existing.qty > 1) {
                return prev.map(c => c.id === itemId ? { ...c, qty: c.qty - 1 } : c);
            }
            return prev.filter(c => c.id !== itemId);
        });
    };

    const clearCart = () => setCart([]);

    const cartTotal = cart.reduce((sum, c) => sum + c.price * c.qty, 0);

    const placeOrder = async () => {
        if (cart.length === 0) return;
        setLoading(true);
        setError('');
        try {
            const res = await api('/canteen/order', {
                method: 'POST',
                body: JSON.stringify({
                    items: cart.map(c => ({ id: c.id, qty: c.qty })),
                }),
            });
            setBill(res.bill);
            setCart([]);
            loadBalance();
            loadOrders();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const viewBill = async (orderId: number) => {
        try {
            const res = await api(`/canteen/orders/${orderId}/bill`);
            setBill(res.bill);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const categories = Array.from(new Set(menu.map(m => m.category)));

    return (
        <>
            <nav className="nav">
                <span className="brand">CampusChain</span>
                <div className="nav-links">
                    <a href="#" onClick={() => router.push('/student')}>← Dashboard</a>
                    <span className="role-badge">Student</span>
                    <a href="#" onClick={() => { clearAuth(); router.push('/'); }}>Logout</a>
                </div>
            </nav>

            <div className="page">
                <h1>🍽️ Campus Canteen</h1>
                <p className="subtitle">Browse the menu, add items to your cart, and pay with CampusTokens.</p>

                {/* Balance Strip */}
                <div className="canteen-balance-strip">
                    <span>💰 Your Balance</span>
                    <span className="canteen-balance-amount">₹{balance}</span>
                </div>

                {/* Tabs */}
                <div className="canteen-tabs">
                    <button
                        className={`canteen-tab ${activeTab === 'menu' ? 'active' : ''}`}
                        onClick={() => setActiveTab('menu')}
                    >
                        🍔 Menu
                    </button>
                    <button
                        className={`canteen-tab ${activeTab === 'orders' ? 'active' : ''}`}
                        onClick={() => setActiveTab('orders')}
                    >
                        📜 My Orders {orders.length > 0 && `(${orders.length})`}
                    </button>
                </div>

                {activeTab === 'menu' && (
                    <>
                        {/* Menu Grid by Category */}
                        {categories.map(cat => (
                            <div key={cat}>
                                <h3 className="canteen-category-title">
                                    {cat === 'food' ? '🍛 Main Course' : cat === 'beverages' ? '☕ Beverages' : '🍟 Snacks'}
                                </h3>
                                <div className="menu-grid">
                                    {menu.filter(m => m.category === cat).map(item => {
                                        const inCart = cart.find(c => c.id === item.id);
                                        return (
                                            <div className="menu-card" key={item.id}>
                                                <div className="menu-emoji">{item.emoji}</div>
                                                <div className="menu-name">{item.name}</div>
                                                <div className="menu-price">₹{item.price}</div>
                                                {inCart ? (
                                                    <div className="menu-qty-controls">
                                                        <button className="qty-btn" onClick={() => removeFromCart(item.id)}>−</button>
                                                        <span className="qty-value">{inCart.qty}</span>
                                                        <button className="qty-btn" onClick={() => addToCart(item)}>+</button>
                                                    </div>
                                                ) : (
                                                    <button className="btn btn-add" onClick={() => addToCart(item)}>
                                                        Add
                                                    </button>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}

                        {/* Cart */}
                        {cart.length > 0 && (
                            <div className="cart-card">
                                <div className="cart-header">
                                    <h2>🛒 Your Cart</h2>
                                    <button className="btn-clear" onClick={clearCart}>Clear All</button>
                                </div>
                                <ul className="cart-list">
                                    {cart.map(c => (
                                        <li className="cart-item" key={c.id}>
                                            <span className="cart-item-info">
                                                {c.emoji} {c.name} × {c.qty}
                                            </span>
                                            <span className="cart-item-price">₹{c.price * c.qty}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div className="cart-total">
                                    <span>Total</span>
                                    <span className="cart-total-amount">₹{cartTotal}</span>
                                </div>
                                {cartTotal > balance && (
                                    <p className="error" style={{ marginTop: '0.5rem' }}>
                                        Insufficient balance! Need ₹{cartTotal - balance} more.
                                    </p>
                                )}
                                <button
                                    className="btn btn-primary btn-order"
                                    onClick={placeOrder}
                                    disabled={loading || cartTotal > balance}
                                >
                                    {loading ? '⏳ Processing on Algorand...' : `Pay ₹${cartTotal} with CampusTokens`}
                                </button>
                                {error && <p className="error">{error}</p>}
                            </div>
                        )}
                    </>
                )}

                {activeTab === 'orders' && (
                    <div className="card">
                        <h2>📜 Order History</h2>
                        {orders.length === 0 ? (
                            <p style={{ color: 'var(--text-muted)' }}>No orders yet. Head to the menu to place one!</p>
                        ) : (
                            <ul className="order-list">
                                {orders.map(o => (
                                    <li className="order-item" key={o.id}>
                                        <div className="order-info">
                                            <div className="order-id">Order #{o.id}</div>
                                            <div className="order-time">{new Date(o.time).toLocaleString()}</div>
                                            <div className="order-items-preview">
                                                {o.items.map((i, idx) => (
                                                    <span key={idx}>{i.emoji} {i.name}{i.qty > 1 ? ` ×${i.qty}` : ''}{idx < o.items.length - 1 ? ', ' : ''}</span>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="order-right">
                                            <div className="order-total">₹{o.total}</div>
                                            <button className="btn btn-secondary btn-sm" onClick={() => viewBill(o.id)}>
                                                View Bill
                                            </button>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </div>

            {/* Bill Modal */}
            {bill && (
                <div className="bill-overlay" onClick={() => setBill(null)}>
                    <div className="bill-modal" onClick={e => e.stopPropagation()}>
                        <div className="bill-header">
                            <div className="bill-logo">🏫</div>
                            <h2>Campus Canteen</h2>
                            <p className="bill-subtitle">CampusChain Digital Receipt</p>
                        </div>

                        <div className="bill-divider" />

                        <div className="bill-meta">
                            <div><strong>Order #</strong> {bill.order_id}</div>
                            <div><strong>Date</strong> {new Date(bill.timestamp).toLocaleString()}</div>
                        </div>

                        <div className="bill-divider" />

                        <table className="bill-table">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th style={{ textAlign: 'center' }}>Qty</th>
                                    <th style={{ textAlign: 'right' }}>Price</th>
                                    <th style={{ textAlign: 'right' }}>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {bill.items.map((item, i) => (
                                    <tr key={i}>
                                        <td>{item.emoji} {item.name}</td>
                                        <td style={{ textAlign: 'center' }}>{item.qty}</td>
                                        <td style={{ textAlign: 'right' }}>₹{item.unit_price}</td>
                                        <td style={{ textAlign: 'right' }}>₹{item.line_total}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        <div className="bill-divider" />

                        <div className="bill-total-row">
                            <span>Grand Total</span>
                            <span className="bill-grand-total">₹{bill.total}</span>
                        </div>

                        <div className="bill-divider" />

                        <div className="bill-footer">
                            <div className="bill-payment">
                                <span className="bill-label">Payment</span>
                                <span>{bill.payment_method}</span>
                            </div>
                            <div className="bill-txn">
                                <span className="bill-label">Algorand Txn</span>
                                <span className="bill-txn-id">{bill.txn_id}</span>
                            </div>
                        </div>

                        <button className="btn btn-primary" onClick={() => setBill(null)} style={{ width: '100%', marginTop: '1.5rem' }}>
                            Close Receipt
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}
