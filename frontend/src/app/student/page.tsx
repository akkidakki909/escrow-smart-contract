'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, getUser, clearAuth } from '@/lib/api';

interface Summary {
    user_id: number;
    username: string;
    month: string;
    total_spent: number;
    balance: number;
    breakdown: { food: number; events: number; stationery: number };
    recent_transactions: { amount: number; category: string; vendor: string; time: string }[];
}

export default function StudentDashboard() {
    const router = useRouter();
    const [summary, setSummary] = useState<Summary | null>(null);
    const [payForm, setPayForm] = useState({ vendor_id: '', amount: '', category: 'food' });
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        const user = getUser();
        if (!user || user.role !== 'student') {
            router.push('/');
            return;
        }
        loadSummary();
    }, []);

    const loadSummary = async () => {
        try {
            const res = await api('/student/summary');
            setSummary(res);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const maxSpend = summary
        ? Math.max(summary.breakdown.food, summary.breakdown.events, summary.breakdown.stationery, 1)
        : 1;

    return (
        <>
            <nav className="nav">
                <span className="brand">CampusChain</span>
                <div className="nav-links">
                    <span className="role-badge">Student</span>
                    <a href="#" onClick={() => { clearAuth(); router.push('/'); }}>Logout</a>
                </div>
            </nav>

            <div className="page">
                <h1>Student Dashboard</h1>
                <p className="subtitle">Your campus wallet — spend at vendors across campus.</p>

                {summary && (
                    <>
                        {/* Profile Card */}
                        <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <h2 style={{ marginBottom: '0.3rem' }}>👤 {summary.username}</h2>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Student Account</p>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Student ID</div>
                                <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--accent)' }}>{summary.user_id}</div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Share this with your parent to link accounts</div>
                            </div>
                        </div>

                        {/* Balance */}
                        <div className="stats">
                            <div className="stat-card">
                                <div className="value">₹{summary.balance}</div>
                                <div className="label">Balance</div>
                            </div>
                            <div className="stat-card">
                                <div className="value" style={{ color: 'var(--orange)' }}>₹{summary.total_spent}</div>
                                <div className="label">Spent This Month</div>
                            </div>
                        </div>

                        {/* Category Breakdown */}
                        <div className="card">
                            <h2>📊 My Spending — {summary.month}</h2>
                            {(['food', 'events', 'stationery'] as const).map((cat) => (
                                <div className="category-bar" key={cat}>
                                    <span className="cat-name">{cat === 'food' ? '🍔 Food' : cat === 'events' ? '🎉 Events' : '📝 Stationery'}</span>
                                    <div className="bar-track">
                                        <div
                                            className={`bar-fill bar-${cat}`}
                                            style={{ width: `${Math.max((summary.breakdown[cat] / maxSpend) * 100, summary.breakdown[cat] > 0 ? 15 : 0)}%` }}
                                        >
                                            {summary.breakdown[cat] > 0 && `₹${summary.breakdown[cat]}`}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Recent Transactions (students CAN see their own) */}
                        {summary.recent_transactions.length > 0 && (
                            <div className="card">
                                <h2>🧾 Recent Transactions</h2>
                                <ul className="txn-list">
                                    {summary.recent_transactions.map((txn, i) => (
                                        <li className="txn-item" key={i}>
                                            <div className="txn-info">
                                                <div className="txn-vendor">{txn.vendor}</div>
                                                <div className="txn-cat">{txn.category}</div>
                                            </div>
                                            <div className="txn-amount">{txn.amount}</div>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                )}
            </div>
        </>
    );
}
