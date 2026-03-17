import React from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { LogIn } from 'lucide-react';

export default function Login() {
    const handleGoogleLogin = () => {
        window.location.href = `${api.defaults.baseURL}/auth/google/login`;
    };

    return (
        <div className="auth-container">
            <div className="card">
                <div className="text-center mb-6">
                    <div style={{ display: 'inline-flex', padding: '1rem', background: 'rgba(79, 70, 229, 0.1)', borderRadius: '50%', marginBottom: '1rem' }}>
                        <LogIn size={32} color="var(--primary)" />
                    </div>
                    <h2>Welcome Back</h2>
                    <p>Continue with Google to access your DairySync dashboard</p>
                </div>

                <button type="button" className="btn btn-primary" onClick={handleGoogleLogin}>
                    Sign in with Google
                </button>

                <p className="text-center mt-4 text-muted">
                    Need access? Ask your admin to invite you.
                </p>

                <p className="text-center mt-2 text-muted">
                    Remembered your password? <Link to="/login">Sign in</Link>
                </p>
            </div>
        </div>
    );
}
