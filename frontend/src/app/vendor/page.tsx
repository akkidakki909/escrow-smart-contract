'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, getUser, clearAuth } from '@/lib/api';

interface OrderItem {
    name: string;
    emoji: string;
    qty: number;
    price: number;
}

interface Order {
    id: number;
    student: string;
    total: number;
    txn_id: string;
    status: string;
    time: string;
    items: OrderItem[];
}

export default function VendorDashboard() {
    const router = useRouter();
    const [registered, setRegistered] = useState(false);
    const [balance, setBalance] = useState(0);
    const [orders, setOrders] = useState<Order[]>([]);

    // Registration form
    const [regName, setRegName] = useState('');
    const [regCategory, setRegCategory] = useState('food');

    // Payment form
    const [studentId, setStudentId] = useState('');
    const [amount, setAmount] = useState('');
    const [category, setCategory] = useState('food');

    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        const user = getUser();
        if (!user || user.role !== 'vendor') {
            router.push('/');
            return;
        }
        checkVendor();
    }, []);

    const checkVendor = async () => {
        try {
            // If QR works, vendor is registered
            await api('/vendor/qr');
            setRegistered(true);
            loadBalance();
            loadOrders();
        } catch {
            setRegistered(false);
        }
    };

    const loadBalance = async () => {
        try {
            const res = await api('/vendor/balance');
            setBalance(res.balance);
        } catch { }
    };

    const loadOrders = async () => {
        try {
            const res = await api('/vendor/orders');
            setOrders(res.orders);
        } catch { }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await api('/vendor/register', {
                method: 'POST',
                body: JSON.stringify({ name: regName, category: regCategory }),
            });
            setRegistered(true);
            setMsg('Vendor registered successfully!');
            loadBalance();
            loadOrders();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handlePayment = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMsg('');
        setError('');
        try {
            await api('/vendor/pay', {
                method: 'POST',
                body: JSON.stringify({
                    student_id: parseInt(studentId),
                    amount: parseInt(amount),
                    category,
                }),
            });
            setMsg(`Payment of ₹${amount} received (${category})`);
            setStudentId('');
            setAmount('');
            loadBalance();
            loadOrders();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <nav className="nav">
                <span className="brand">CampusChain</span>
                <div className="nav-links">
                    <span className="role-badge">Vendor</span>
                    <a href="#" onClick={() => { clearAuth(); router.push('/'); }}>Logout</a>
                </div>
            </nav>

            <div className="page">
                <h1>Vendor Dashboard</h1>
                <p className="subtitle">Accept CampusToken payments from students.</p>

                {!registered ? (
                    <div className="card">
                        <h2>📋 Register Your Vendor</h2>
                        <form onSubmit={handleRegister}>
                            <div className="form-group">
                                <label>Vendor Name</label>
                                <input
                                    type="text"
                                    value={regName}
                                    onChange={(e) => setRegName(e.target.value)}
                                    placeholder="e.g. Campus Canteen"
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Category</label>
                                <select value={regCategory} onChange={(e) => setRegCategory(e.target.value)}>
                                    <option value="food">🍔 Food</option>
                                    <option value="events">🎉 Events</option>
                                    <option value="stationery">📝 Stationery</option>
                                </select>
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={loading}>
                                {loading ? 'Registering...' : 'Register Vendor'}
                            </button>
                        </form>
                        {error && <p className="error">{error}</p>}
                    </div>
                ) : (
                    <>
                        <div className="stats">
                            <div className="stat-card">
                                <div className="value" style={{ color: 'var(--green)' }}>₹{balance}</div>
                                <div className="label">Tokens Received</div>
                            </div>
                            <div className="stat-card">
                                <div className="value">{orders.length}</div>
                                <div className="label">Total Orders</div>
                            </div>
                        </div>

                        {/* Incoming Orders Feed */}
                        <div className="card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                <h2 style={{ marginBottom: 0 }}>📋 Incoming Orders</h2>
                                <button className="btn btn-secondary btn-sm" onClick={loadOrders}>↻ Refresh</button>
                            </div>

                            {orders.length === 0 ? (
                                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>
                                    No orders yet. Students can order from the canteen menu.
                                </p>
                            ) : (
                                <ul className="vendor-order-list">
                                    {orders.map(o => (
                                        <li className="vendor-order-item" key={o.id}>
                                            <div className="vendor-order-header">
                                                <div>
                                                    <span className="vendor-order-id">Order #{o.id}</span>
                                                    <span className="vendor-order-student">👤 {o.student}</span>
                                                </div>
                                                <div className="vendor-order-total">₹{o.total}</div>
                                            </div>
                                            <div className="vendor-order-items">
                                                {o.items.map((item, idx) => (
                                                    <span className="vendor-order-chip" key={idx}>
                                                        {item.emoji} {item.name} {item.qty > 1 ? `×${item.qty}` : ''}
                                                    </span>
                                                ))}
                                            </div>
                                            <div className="vendor-order-time">
                                                {new Date(o.time).toLocaleString()}
                                                <span className="vendor-order-status">✅ Paid</span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {/* Manual payment (for non-canteen purchases) */}
                        <div className="card">
                            <h2>💳 Manual Payment</h2>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '1rem' }}>
                                For walk-up purchases not through the canteen menu.
                            </p>
                            <form onSubmit={handlePayment}>
                                <div className="form-group">
                                    <label>Student ID</label>
                                    <input
                                        type="number"
                                        value={studentId}
                                        onChange={(e) => setStudentId(e.target.value)}
                                        placeholder="Enter student's user ID"
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Amount (₹)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={amount}
                                        onChange={(e) => setAmount(e.target.value)}
                                        placeholder="e.g. 50"
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Category</label>
                                    <select value={category} onChange={(e) => setCategory(e.target.value)}>
                                        <option value="food">🍔 Food</option>
                                        <option value="events">🎉 Events</option>
                                        <option value="stationery">📝 Stationery</option>
                                    </select>
                                </div>
                                <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                                    {loading ? 'Processing...' : 'Accept Payment'}
                                </button>
                            </form>
                            {msg && <p className="success">{msg}</p>}
                            {error && <p className="error">{error}</p>}
                        </div>
                    </>
                )}
            </div>
        </>
    );
}
