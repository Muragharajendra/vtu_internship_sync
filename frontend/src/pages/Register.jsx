import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { UserPlus } from 'lucide-react';

export default function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await api.post('/register', { email, password });
            // auto login
            const res = await api.post('/login', { email, password });
            localStorage.setItem('token', res.data.access_token);
            navigate('/dashboard');
            window.location.reload();
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="card">
                <div className="text-center mb-6">
                    <div style={{ display: 'inline-flex', padding: '1rem', background: 'rgba(79, 70, 229, 0.1)', borderRadius: '50%', marginBottom: '1rem' }}>
                        <UserPlus size={32} color="var(--primary)" />
                    </div>
                    <h2>Create Account</h2>
                    <p>Get started with OneTouch</p>
                </div>

                <form onSubmit={handleRegister}>
                    <div className="form-group">
                        <label className="form-label">Email Address</label>
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
                        {loading ? <div className="spinner"></div> : 'Create Account'}
                    </button>
                </form>

                <p className="text-center mt-4 text-muted">
                    Already have an account? <Link to="/login">Sign in</Link>
                </p>
            </div>
        </div>
    );
}
