import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function ChangePassword() {
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleChange = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!oldPassword || !newPassword || !confirmPassword) {
            setError('Please fill out all fields.');
            return;
        }

        if (newPassword !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        setLoading(true);
        try {
            await api.post('/change-password', { old_password: oldPassword, new_password: newPassword });
            setMessage('Password changed successfully. Please log in again.');
            setTimeout(() => {
                localStorage.removeItem('token');
                navigate('/login');
            }, 1200);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to change password');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="card">
                <div className="text-center mb-6">
                    <h2>Change Password</h2>
                    <p>Enter your current and new password.</p>
                </div>

                <form onSubmit={handleChange}>
                    <div className="form-group">
                        <label className="form-label">Current Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={oldPassword}
                            onChange={(e) => setOldPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">New Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Confirm New Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>

                    {error && <p className="error-text mb-4">{error}</p>}
                    {message && <p className="text-success mb-4">{message}</p>}

                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? <div className="spinner"></div> : 'Change Password'}
                    </button>
                </form>

                <p className="text-center mt-4 text-muted">
                    Back to <a href="/dashboard">Dashboard</a>
                </p>
            </div>
        </div>
    );
}
