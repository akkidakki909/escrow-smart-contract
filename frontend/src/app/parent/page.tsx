'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, getUser, clearAuth } from '@/lib/api';

interface SpendingData {
    student_name: string;
    month: string;
    total_funded: number;
    total_spent: number;
    balance: number;
    breakdown: { food: number; events: number; stationery: number };
}

interface Student {
    id: number;
    name: string;
}

export default function ParentDashboard() {
    const router = useRouter();
    const [students, setStudents] = useState<Student[]>([]);
    const [selectedStudent, setSelectedStudent] = useState<number | null>(null);
    const [spending, setSpending] = useState<SpendingData | null>(null);
    const [fundAmount, setFundAmount] = useState('');
    const [linkStudentId, setLinkStudentId] = useState('');
    const [loading, setLoading] = useState(false);
    const [fundMsg, setFundMsg] = useState('');
    const [linkMsg, setLinkMsg] = useState('');
    const [error, setError] = useState('');

    const currentMonth = new Date().toISOString().slice(0, 7);

    useEffect(() => {
        const user = getUser();
        if (!user || user.role !== 'parent') {
            router.push('/');
            return;
        }
        loadStudents();
    }, []);

    useEffect(() => {
        if (selectedStudent) loadSpending();
    }, [selectedStudent]);

    const loadStudents = async () => {
        try {
            const res = await api('/parent/students');
            setStudents(res.students);
            if (res.students.length > 0) {
                setSelectedStudent(res.students[0].id);
            }
        } catch (err: any) {
            setError(err.message);
        }
    };

    const loadSpending = async () => {
        if (!selectedStudent) return;
        try {
            const res = await api(`/parent/spending?student_id=${selectedStudent}&month=${currentMonth}`);
            setSpending(res);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleFund = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedStudent || !fundAmount) return;
        setLoading(true);
        setFundMsg('');
        setError('');

        try {
            const res = await api('/parent/fund', {
                method: 'POST',
                body: JSON.stringify({ student_id: selectedStudent, amount: parseInt(fundAmount) }),
            });
            setFundMsg(res.message);
            setFundAmount('');
            loadSpending();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleLinkStudent = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!linkStudentId) return;
        setLoading(true);
        setLinkMsg('');
        setError('');
        try {
            const user = getUser();
            await api('/auth/link-student', {
                method: 'POST',
                body: JSON.stringify({ parent_id: user?.user_id, student_id: parseInt(linkStudentId) }),
            });
            setLinkMsg('Student linked successfully!');
            setLinkStudentId('');
            loadStudents();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const maxSpend = spending
        ? Math.max(spending.breakdown.food, spending.breakdown.events, spending.breakdown.stationery, 1)
        : 1;

    return (
        <>
            <nav className="nav">
                <span className="brand">CampusChain</span>
                <div className="nav-links">
                    <span className="role-badge">Parent</span>
                    <a href="#" onClick={() => { clearAuth(); router.push('/'); }}>Logout</a>
                </div>
            </nav>

            <div className="page">
                <h1>Parent Dashboard</h1>
                <p className="subtitle">Fund your child's campus wallet and track spending by category.</p>

                {students.length === 0 ? (
                    <div className="card">
                        <h2>🔗 Link a Student</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                            Enter your child's Student ID to link your accounts. They can find their ID on their Student Dashboard.
                        </p>
                        <form onSubmit={handleLinkStudent} style={{ display: 'flex', gap: '0.8rem', alignItems: 'end' }}>
                            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                                <label>Student ID</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={linkStudentId}
                                    onChange={(e) => setLinkStudentId(e.target.value)}
                                    placeholder="e.g. 1"
                                    required
                                />
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={loading}>
                                {loading ? 'Linking...' : 'Link'}
                            </button>
                        </form>
                        {linkMsg && <p className="success">{linkMsg}</p>}
                        {error && <p className="error">{error}</p>}
                    </div>
                ) : (
                    <>
                        {students.length > 1 && (
                            <div className="form-group">
                                <label>Select Student</label>
                                <select
                                    value={selectedStudent || ''}
                                    onChange={(e) => setSelectedStudent(parseInt(e.target.value))}
                                >
                                    {students.map((s) => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* Fund Card */}
                        <div className="card">
                            <h2>💰 Add Funds (Simulated UPI)</h2>
                            <form onSubmit={handleFund} style={{ display: 'flex', gap: '0.8rem', alignItems: 'end' }}>
                                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                                    <label>Amount (₹)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={fundAmount}
                                        onChange={(e) => setFundAmount(e.target.value)}
                                        placeholder="e.g. 500"
                                        required
                                    />
                                </div>
                                <button type="submit" className="btn btn-primary" disabled={loading}>
                                    {loading ? 'Sending...' : 'Fund'}
                                </button>
                            </form>
                            {fundMsg && <p className="success">{fundMsg}</p>}
                            {error && <p className="error">{error}</p>}
                        </div>

                        {/* Stats */}
                        {spending && (
                            <>
                                <div className="stats">
                                    <div className="stat-card">
                                        <div className="value">₹{spending.balance}</div>
                                        <div className="label">Balance</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="value" style={{ color: 'var(--green)' }}>₹{spending.total_funded}</div>
                                        <div className="label">Funded This Month</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="value" style={{ color: 'var(--orange)' }}>₹{spending.total_spent}</div>
                                        <div className="label">Spent This Month</div>
                                    </div>
                                </div>

                                {/* Category Breakdown */}
                                <div className="card">
                                    <h2>📊 Spending by Category — {spending.month}</h2>
                                    {(['food', 'events', 'stationery'] as const).map((cat) => (
                                        <div className="category-bar" key={cat}>
                                            <span className="cat-name">{cat === 'food' ? '🍔 Food' : cat === 'events' ? '🎉 Events' : '📝 Stationery'}</span>
                                            <div className="bar-track">
                                                <div
                                                    className={`bar-fill bar-${cat}`}
                                                    style={{ width: `${Math.max((spending.breakdown[cat] / maxSpend) * 100, spending.breakdown[cat] > 0 ? 15 : 0)}%` }}
                                                >
                                                    {spending.breakdown[cat] > 0 && `₹${spending.breakdown[cat]}`}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <div className="card" style={{ background: 'transparent', border: '1px dashed var(--border)', textAlign: 'center' }}>
                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                        🔒 Individual transactions, merchant names, and timestamps are <strong>not visible</strong> to parents.
                                        <br />Only aggregated category totals are shown — powered by the CampusChain privacy model.
                                    </p>
                                </div>
                            </>
                        )}
                    </>
                )}
            </div>
        </>
    );
}
