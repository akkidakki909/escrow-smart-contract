'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, getUser, clearAuth } from '@/lib/api';

interface Stats {
    users: { students: number; parents: number; vendors: number };
    financials: { total_funded: number; total_spent: number; total_transactions: number };
    spending_by_category: { food?: number; events?: number; stationery?: number };
}

export default function AdminDashboard() {
    const router = useRouter();
    const [stats, setStats] = useState<Stats | null>(null);
    const [error, setError] = useState('');

    useEffect(() => {
        const user = getUser();
        if (!user || user.role !== 'admin') {
            router.push('/');
            return;
        }
        loadStats();
    }, []);

    const loadStats = async () => {
        try {
            const res = await api('/admin/stats');
            setStats(res);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const maxCat = stats
        ? Math.max(
            stats.spending_by_category.food || 0,
            stats.spending_by_category.events || 0,
            stats.spending_by_category.stationery || 0,
            1
        )
        : 1;

    return (
        <>
            <nav className="nav">
                <span className="brand">CampusChain</span>
                <div className="nav-links">
                    <span className="role-badge">Admin</span>
                    <a href="#" onClick={() => { clearAuth(); router.push('/'); }}>Logout</a>
                </div>
            </nav>

            <div className="page">
                <h1>Admin Dashboard</h1>
                <p className="subtitle">System-wide overview of the CampusChain network.</p>

                {error && <p className="error">{error}</p>}

                {stats && (
                    <>
                        <div className="stats">
                            <div className="stat-card">
                                <div className="value">{stats.users.students}</div>
                                <div className="label">Students</div>
                            </div>
                            <div className="stat-card">
                                <div className="value">{stats.users.parents}</div>
                                <div className="label">Parents</div>
                            </div>
                            <div className="stat-card">
                                <div className="value">{stats.users.vendors}</div>
                                <div className="label">Vendors</div>
                            </div>
                        </div>

                        <div className="stats">
                            <div className="stat-card">
                                <div className="value" style={{ color: 'var(--green)' }}>₹{stats.financials.total_funded}</div>
                                <div className="label">Total Funded</div>
                            </div>
                            <div className="stat-card">
                                <div className="value" style={{ color: 'var(--orange)' }}>₹{stats.financials.total_spent}</div>
                                <div className="label">Total Spent</div>
                            </div>
                            <div className="stat-card">
                                <div className="value" style={{ color: 'var(--blue)' }}>{stats.financials.total_transactions}</div>
                                <div className="label">Transactions</div>
                            </div>
                        </div>

                        <div className="card">
                            <h2>📊 All-Time Spending by Category</h2>
                            {(['food', 'events', 'stationery'] as const).map((cat) => {
                                const val = stats.spending_by_category[cat] || 0;
                                return (
                                    <div className="category-bar" key={cat}>
                                        <span className="cat-name">{cat === 'food' ? '🍔 Food' : cat === 'events' ? '🎉 Events' : '📝 Stationery'}</span>
                                        <div className="bar-track">
                                            <div
                                                className={`bar-fill bar-${cat}`}
                                                style={{ width: `${Math.max((val / maxCat) * 100, val > 0 ? 15 : 0)}%` }}
                                            >
                                                {val > 0 && `₹${val}`}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}
            </div>
        </>
    );
}
