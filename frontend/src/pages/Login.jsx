import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { LogIn } from 'lucide-react';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const res = await api.post('/login', { email, password });
            localStorage.setItem('token', res.data.access_token);
            navigate('/dashboard');
            window.location.reload();
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="card">
                <div className="text-center mb-6">
                    <div style={{ display: 'inline-flex', padding: '1rem', background: 'rgba(79, 70, 229, 0.1)', borderRadius: '50%', marginBottom: '1rem' }}>
                        <LogIn size={32} color="var(--primary)" />
                    </div>
                    <h2>Welcome Back</h2>
                    <p>Login to your DairySync dashboard</p>
                </div>

                <form onSubmit={handleLogin}>
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input
                            type="email"
                            className="form-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    {error && <p className="error-text mb-4">{error}</p>}

                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? <div className="spinner"></div> : 'Sign In'}
                    </button>
                </form>

                <p className="text-center mt-4 text-muted">
                    Don't have an account? <Link to="/register">Sign up</Link>
                </p>
            </div>
        </div>
    );
}
