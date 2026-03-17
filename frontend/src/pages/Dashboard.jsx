import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import api from '../api';
import { LogOut, Play, Settings, Database, Activity } from 'lucide-react';

export default function Dashboard() {
    const [user, setUser] = useState(null);
    const [dateFilter, setDateFilter] = useState('2026-02-03');
    const [sourceEmail, setSourceEmail] = useState('');
    const [sourcePassword, setSourcePassword] = useState('');
    const [destEmail, setDestEmail] = useState('');
    const [destPassword, setDestPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const location = useLocation();

    const fetchUser = async () => {
        try {
            const res = await api.get('/me');
            setUser(res.data);
        } catch (err) {
            if (err.response?.status === 401) {
                localStorage.removeItem('token');
                navigate('/login');
            }
        }
    };

    useEffect(() => {
        fetchUser();
    }, []);

    const handleStartSync = async () => {
        if (user?.entries_remaining <= 0) {
            setError('You need to purchase entries first.');
            return;
        }
        if (!sourceEmail || !sourcePassword || !destEmail || !destPassword) {
            setError('Please provide source and target emails and passwords.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            const payload = {
                start_date: dateFilter,
                source_email: sourceEmail,
                source_password: sourcePassword,
                dest_email: destEmail,
                dest_password: destPassword
            };
            const res = await api.post('/start-sync', payload);
            navigate(`/job/${res.data.job_id}`);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to start sync');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    if (!user) return <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}><div className="spinner" style={{ borderColor: 'var(--primary)', borderLeftColor: 'transparent' }}></div></div>;

    return (
        <div className="app-container">
            <nav className="navbar">
                <div className="nav-brand">
                    <Activity size={24} color="var(--primary)" />
                    DairySync
                </div>
                <div className="nav-links">
                    <Link to="/dashboard" className={location.pathname === '/dashboard' ? 'active-nav' : 'text-muted'}>Dashboard</Link>
                    <Link to="/billing" className={location.pathname === '/billing' ? 'active-nav' : 'text-muted'}>Billing</Link>
                    <span style={{ marginLeft: '1rem', borderLeft: '1px solid var(--border-color)', paddingLeft: '1rem' }}>{user.email}</span>
                    <button className="btn btn-secondary" onClick={handleLogout} style={{ padding: '0.4rem 1rem' }}>
                        <LogOut size={16} /> <span style={{ marginLeft: '0.5rem' }}>Logout</span>
                    </button>
                </div>
            </nav>

            <main className="container">
                <div className="mb-6" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <div>
                        <h2>Dashboard Overview</h2>
                        <p>Configure mapping and automate your internship diary</p>
                    </div>
                    <div className="card stat-card" style={{ padding: '1rem 2rem', border: '1px solid var(--border-color)', background: 'var(--card-bg)', minWidth: '200px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <h4 style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Entries Available</h4>
                        <div className="stat-value" style={{ fontSize: '2rem', margin: '0.25rem 0' }}>{user.entries_remaining}</div>
                        {user.entries_remaining === 0 && <Link to="/billing" style={{ fontSize: '0.875rem' }}>Top up now &rarr;</Link>}
                    </div>
                </div>

                {error && <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1.5rem', border: '1px solid var(--error)' }}>{error}</div>}

                <div className="card" style={{ maxWidth: '800px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
                        <Settings size={20} color="var(--primary)" />
                        <h3 style={{ margin: 0 }}>Synchronization Settings</h3>
                    </div>

                    <div className="form-group mb-6">
                        <label className="form-label">Earliest Date to Sync</label>
                        <p className="text-muted mb-2" style={{ fontSize: '0.875rem' }}>The exact point in time the script should start copying from.</p>
                        <input type="date" className="form-input" style={{ maxWidth: '300px' }} value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} />
                    </div>

                    <div className="grid-2 gap-4 mb-6" style={{ gridTemplateColumns: '1fr 1fr', background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '0.5rem' }}>
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                                <Database size={16} color="var(--text-muted)" />
                                <h4 style={{ margin: 0 }}>Source Account (Copy From)</h4>
                            </div>
                            <div className="form-group mb-4">
                                <label className="form-label text-muted">Portal Email</label>
                                <input type="email" className="form-input" value={sourceEmail} onChange={(e) => setSourceEmail(e.target.value)} placeholder="student-1@vtu.ac.in" />
                            </div>
                            <div className="form-group mb-0">
                                <label className="form-label text-muted">Password</label>
                                <input type="password" className="form-input" value={sourcePassword} onChange={(e) => setSourcePassword(e.target.value)} placeholder="••••••••" />
                            </div>
                        </div>

                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                                <Database size={16} color="var(--text-muted)" />
                                <h4 style={{ margin: 0 }}>Target Account (Paste To)</h4>
                            </div>
                            <div className="form-group mb-4">
                                <label className="form-label text-muted">Portal Email</label>
                                <input type="email" className="form-input" value={destEmail} onChange={(e) => setDestEmail(e.target.value)} placeholder="student-2@vtu.ac.in" />
                            </div>
                            <div className="form-group mb-0">
                                <label className="form-label text-muted">Password</label>
                                <input type="password" className="form-input" value={destPassword} onChange={(e) => setDestPassword(e.target.value)} placeholder="••••••••" />
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
                        {user.entries_remaining <= 0 && <span className="error-text">Insufficient balance. Please purchase a plan.</span>}
                        <button className="btn btn-primary" style={{ width: 'auto', padding: '0.75rem 2rem' }} onClick={handleStartSync} disabled={loading || user.entries_remaining <= 0}>
                            <Play size={18} style={{ marginRight: '0.5rem' }} /> Execute Live Sync
                        </button>
                    </div>
                </div>

            </main>
        </div>
    );
}
