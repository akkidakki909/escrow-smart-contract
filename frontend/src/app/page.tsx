'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, setToken, setUser } from '@/lib/api';

export default function Home() {
    const router = useRouter();
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('student');
    const [linkedStudent, setLinkedStudent] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);

        try {
            if (mode === 'register') {
                const body: any = { username, password, role };
                if (role === 'parent' && linkedStudent) {
                    body.linked_student_id = parseInt(linkedStudent);
                }
                const res = await api('/auth/register', {
                    method: 'POST',
                    body: JSON.stringify(body),
                });
                setSuccess(`Registered! User ID: ${res.user_id}. You can now login.`);
                setMode('login');
            } else {
                const res = await api('/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ username, password }),
                });
                setToken(res.token);
                setUser({ user_id: res.user_id, role: res.role });

                // Route to role-specific dashboard
                const routes: Record<string, string> = {
                    student: '/student',
                    parent: '/parent',
                    vendor: '/vendor',
                    admin: '/admin',
                };
                router.push(routes[res.role] || '/');
            }
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page" style={{ maxWidth: 450, marginTop: '8vh' }}>
            <h1>CampusChain</h1>
            <p className="subtitle">Programmable Campus Wallet on Algorand</p>

            <div className="card">
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                    <button
                        className={mode === 'login' ? 'btn btn-primary' : 'btn btn-secondary'}
                        onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
                        style={{ flex: 1 }}
                    >
                        Login
                    </button>
                    <button
                        className={mode === 'register' ? 'btn btn-primary' : 'btn btn-secondary'}
                        onClick={() => { setMode('register'); setError(''); setSuccess(''); }}
                        style={{ flex: 1 }}
                    >
                        Register
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Enter username"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter password"
                            required
                        />
                    </div>

                    {mode === 'register' && (
                        <>
                            <div className="form-group">
                                <label>Role</label>
                                <select value={role} onChange={(e) => setRole(e.target.value)}>
                                    <option value="student">Student</option>
                                    <option value="parent">Parent</option>
                                    <option value="vendor">Vendor</option>
                                </select>
                            </div>

                            {role === 'parent' && (
                                <div className="form-group">
                                    <label>Link to Student ID (optional)</label>
                                    <input
                                        type="number"
                                        value={linkedStudent}
                                        onChange={(e) => setLinkedStudent(e.target.value)}
                                        placeholder="Student's user ID"
                                    />
                                </div>
                            )}
                        </>
                    )}

                    <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                        {loading ? 'Processing...' : mode === 'login' ? 'Login' : 'Register'}
                    </button>

                    {error && <p className="error">{error}</p>}
                    {success && <p className="success">{success}</p>}
                </form>
            </div>

            <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                No wallet or crypto required. Just sign up and go.
            </p>
        </div>
    );
}
