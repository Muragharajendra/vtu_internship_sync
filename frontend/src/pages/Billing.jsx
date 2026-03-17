import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import api from '../api';
import { LogOut, Activity, CreditCard, Award, CheckCircle, Ticket, X, Smartphone } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export default function Billing() {
    const [user, setUser] = useState(null);
    const [couponCode, setCouponCode] = useState('');
    const [activeCoupon, setActiveCoupon] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Payment Modal State
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [selectedPlanId, setSelectedPlanId] = useState('');
    const [paymentAmount, setPaymentAmount] = useState(0);
    const [utr, setUtr] = useState('');

    // New Swiggy-style mock states
    const [paymentStep, setPaymentStep] = useState('selection'); // 'selection', 'processing', 'success'
    const [selectedMethod, setSelectedMethod] = useState('');

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

    const handleApplyCoupon = () => {
        if (!couponCode) return;
        setActiveCoupon(couponCode);
        if (couponCode === 'FREETRIAL') {
            setError(''); // Clear errors if applying fresh
        }
    };

    const calculateDiscountedPrice = (basePrice) => {
        if (activeCoupon === 'DISCOUNTOFFER10') return basePrice * 0.90;
        if (activeCoupon === 'FREETRIAL') return 0;
        return basePrice;
    };

    const loadRazorpayScript = () => {
        return new Promise((resolve, reject) => {
            if (window.Razorpay) {
                return resolve(true);
            }
            const script = document.createElement('script');
            script.src = 'https://checkout.razorpay.com/v1/checkout.js';
            script.onload = () => resolve(true);
            script.onerror = () => reject(new Error('Razorpay script failed to load'));
            document.body.appendChild(script);
        });
    };

    const verifyRazorpayPayment = async (payload) => {
        setLoading(true);
        setError('');

        try {
            const res = await api.post('/checkout/verify', payload);
            alert(`Success! Added ${res.data.entries_added} entries to your account.`);
            setCouponCode('');
            setActiveCoupon(null);
            setShowPaymentModal(false);
            fetchUser();
        } catch (err) {
            setError(err.response?.data?.detail || 'Payment verification failed');
        } finally {
            setLoading(false);
        }
    };

    const initiateCheckout = async (planId, basePrice) => {
        const finalPrice = calculateDiscountedPrice(basePrice);

        if (finalPrice <= 0) {
            executeCheckout(planId);
            return;
        }

        setLoading(true);
        setError('');

        try {
            const res = await api.post('/checkout', { plan_id: planId, coupon: activeCoupon || '' });

            // If backend returned Razorpay order info, open Razorpay checkout modal
            if (res.data.order_id && res.data.key_id) {
                await loadRazorpayScript();

                const options = {
                    key: res.data.key_id,
                    amount: Math.round(finalPrice * 100),
                    currency: res.data.currency || 'INR',
                    name: 'VTU Auto Sync',
                    description: `Payment for ${planId}`,
                    order_id: res.data.order_id,
                    handler: (response) => {
                        verifyRazorpayPayment(response);
                    },
                    prefill: {
                        email: user?.email,
                    },
                    theme: {
                        color: '#4f46e5',
                    },
                };

                const rzp = new window.Razorpay(options);
                rzp.open();

                return;
            }

            // Fallback to manual UPI flow
            setSelectedPlanId(planId);
            setPaymentAmount(finalPrice);
            setShowPaymentModal(true);
        } catch (err) {
            setError(err.response?.data?.detail || 'Checkout initiation failed');
            setShowPaymentModal(true);
        } finally {
            setLoading(false);
        }
    };

    const executeCheckout = async (planId, overrideUtr = null) => {
        setLoading(true);
        setError('');
        try {
            const res = await api.post('/checkout', { plan_id: planId, coupon: activeCoupon || '', utr: overrideUtr || utr });
            alert(`Success! Added ${res.data.entries_added} entries to your account.`);
            setCouponCode('');
            setActiveCoupon(null);
            setShowPaymentModal(false);
            fetchUser();
        } catch (err) {
            setError(err.response?.data?.detail || 'Checkout verify failed');
            setShowPaymentModal(false);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    if (!user) return <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}><div className="spinner" style={{ borderColor: 'var(--primary)', borderLeftColor: 'transparent' }}></div></div>;

    // Generate UPI URI
    const upiId = "muragharajendra@oksbi";
    const upiName = "VTU Sync Automator";
    const upiUri = `upi://pay?pa=${upiId}&pn=${encodeURIComponent(upiName)}&am=${paymentAmount}&cu=INR&tn=${encodeURIComponent(`VTU Sync Plan ${selectedPlanId}`)}`;

    return (
        <div className="app-container">
            <nav className="navbar">
                <div className="nav-brand">
                    <Activity size={24} color="var(--primary)" />
                    VTU Automator
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
                <div className="mb-6">
                    <h2>Billing & Subscriptions</h2>
                    <p>Top up your account balance to automate more diary entries</p>
                </div>

                {error && <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1.5rem', border: '1px solid var(--error)' }}>{error}</div>}

                {/* PROMO CARDS */}
                <div className="grid-2 gap-4 mb-6">
                    {/* Basic Plan */}
                    <div className="card" style={{ border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', height: '100%' }}>
                        <div style={{ flexGrow: 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                                <div>
                                    <h3 style={{ fontSize: '1.5rem', margin: 0 }}>Basic Plan</h3>
                                    <p className="text-muted">For small backlogs</p>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    {activeCoupon && activeCoupon !== 'FREETRIAL' ? (
                                        <>
                                            <h2 style={{ color: 'var(--text-muted)', textDecoration: 'line-through', fontSize: '1.25rem', margin: 0 }}>₹100</h2>
                                            <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹{calculateDiscountedPrice(100)}</h2>
                                        </>
                                    ) : activeCoupon === 'FREETRIAL' ? (
                                        <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹0</h2>
                                    ) : (
                                        <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹100</h2>
                                    )}
                                </div>
                            </div>
                            <ul style={{ listStyle: 'none', margin: '2rem 0', color: 'var(--text-muted)' }}>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--success)" /> Sync up to 30 diary entries</li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--success)" /> Live log tracker</li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--success)" /> Email support</li>
                            </ul>
                            {activeCoupon === 'FREETRIAL' && (
                                <p style={{ fontSize: '0.875rem', color: 'var(--primary)', fontStyle: 'italic', marginBottom: '1rem' }}>* FREETRIAL applied: Gives exactly 2 entries limit.</p>
                            )}
                        </div>
                        <button className="btn btn-secondary w-full" onClick={() => initiateCheckout('plan_30', 100)} disabled={loading}>
                            <CreditCard size={18} style={{ marginRight: '0.5rem' }} /> {activeCoupon === 'FREETRIAL' ? "Claim Freetrial" : "Purchase Now"}
                        </button>
                    </div>

                    {/* Pro Plan */}
                    <div className="card" style={{ border: '2px solid var(--primary)', background: 'linear-gradient(to bottom right, rgba(79,70,229,0.05), transparent)', display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
                        <div style={{ position: 'absolute', top: '-12px', right: '24px', background: 'var(--primary)', color: 'white', padding: '0.25rem 1rem', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: 'bold', textTransform: 'uppercase' }}>Most Popular</div>
                        <div style={{ flexGrow: 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                                <div>
                                    <h3 style={{ fontSize: '1.5rem', margin: 0 }}>Pro Plan</h3>
                                    <p className="text-muted">Automate entire semesters</p>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    {activeCoupon && activeCoupon !== 'FREETRIAL' ? (
                                        <>
                                            <h2 style={{ color: 'var(--text-muted)', textDecoration: 'line-through', fontSize: '1.25rem', margin: 0 }}>₹150</h2>
                                            <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹{calculateDiscountedPrice(150)}</h2>
                                        </>
                                    ) : activeCoupon === 'FREETRIAL' ? (
                                        <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹0</h2>
                                    ) : (
                                        <h2 style={{ color: 'var(--primary)', margin: 0 }}>₹150</h2>
                                    )}
                                </div>
                            </div>
                            <ul style={{ listStyle: 'none', margin: '2rem 0', color: 'var(--text-main)' }}>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--primary)" /> Sync up to 60 diary entries</li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--primary)" /> Faster background queueing</li>
                                <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}><CheckCircle size={16} color="var(--primary)" /> Priority Support</li>
                            </ul>
                            {activeCoupon === 'FREETRIAL' && (
                                <p style={{ fontSize: '0.875rem', color: 'var(--primary)', fontStyle: 'italic', marginBottom: '1rem' }}>* FREETRIAL applied: Gives exactly 2 entries limit.</p>
                            )}
                        </div>
                        <button className="btn btn-primary w-full" onClick={() => initiateCheckout('plan_60', 150)} disabled={loading}>
                            <Award size={18} style={{ marginRight: '0.5rem' }} /> {activeCoupon === 'FREETRIAL' ? "Claim Freetrial" : "Purchase Pro"}
                        </button>
                    </div>
                </div>

                <div className="card" style={{ maxWidth: '500px', marginTop: '3rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                        <Ticket size={24} color="var(--text-muted)" />
                        <h3 style={{ margin: 0 }}>Promotions</h3>
                    </div>
                    <div className="form-group mb-0">
                        <label className="form-label">Enter Coupon Code</label>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <input type="text" className="form-input" placeholder="e.g. FREETRIAL" value={couponCode} onChange={(e) => setCouponCode(e.target.value)} style={{ flexGrow: 1 }} />
                            <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={handleApplyCoupon}>Apply</button>
                        </div>
                        {activeCoupon && <p className="text-success mt-2" style={{ color: 'var(--success)', fontSize: '0.875rem' }}>Coupon "{activeCoupon}" applied! {activeCoupon === 'FREETRIAL' ? '(Limit 1 per account, 2 Entries)' : 'Discount is reflected above.'}</p>}
                    </div>
                </div>

            </main>

            {/* UPI Payment Modal */}
            {showPaymentModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(4px)',
                    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 100
                }}>
                    <div className="card" style={{ maxWidth: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem' }}>
                        <button
                            onClick={() => setShowPaymentModal(false)}
                            style={{ alignSelf: 'flex-end', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', marginBottom: '1rem' }}
                        >
                            <X size={24} />
                        </button>
                        <h3 style={{ marginBottom: '0.5rem' }}>Scan to Pay</h3>
                        <p className="text-muted text-center mb-6">Complete your payment of <b>₹{paymentAmount}</b> using any UPI App</p>

                        <div style={{ background: 'white', padding: '1rem', borderRadius: '1rem', marginBottom: '1.5rem' }}>
                            <QRCodeSVG value={upiUri} size={200} />
                        </div>

                        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', marginBottom: '1.5rem', textAlign: 'center', width: '100%' }}>
                            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', margin: 0 }}>UPI ID</p>
                            <p style={{ fontSize: '1rem', fontWeight: 'bold', margin: '0.25rem 0 0 0' }}>{upiId}</p>
                        </div>

                        <div className="form-group mb-4 w-full" style={{ width: '100%' }}>
                            <label className="form-label text-left" style={{ textAlign: 'left', display: 'block' }}>Enter 12-Digit UTR No.</label>
                            <input type="text" className="form-input" placeholder="e.g. 312345678901" value={utr} onChange={(e) => setUtr(e.target.value)} maxLength={12} />
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', textAlign: 'left' }}>Found in your UPI app transaction history.</p>
                        </div>

                        <div style={{ display: 'flex', gap: '1rem', width: '100%', flexWrap: 'wrap' }}>
                            <h4 style={{ width: '100%', textAlign: 'center', margin: '0 0 0.5rem 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Or open directly in app:</h4>
                            <a href={`gpay://upi/pay?pa=${upiId}&pn=${encodeURIComponent(upiName)}&am=${paymentAmount}&cu=INR`} className="btn btn-secondary" style={{ flex: 1, textDecoration: 'none', padding: '0.5rem', fontSize: '0.875rem' }}>
                                GPay
                            </a>
                            <a href={`phonepe://pay?pa=${upiId}&pn=${encodeURIComponent(upiName)}&am=${paymentAmount}&cu=INR`} className="btn btn-secondary" style={{ flex: 1, textDecoration: 'none', padding: '0.5rem', fontSize: '0.875rem' }}>
                                PhonePe
                            </a>
                            <a href={`paytmmp://pay?pa=${upiId}&pn=${encodeURIComponent(upiName)}&am=${paymentAmount}&cu=INR`} className="btn btn-secondary" style={{ flex: 1, textDecoration: 'none', padding: '0.5rem', fontSize: '0.875rem' }}>
                                Paytm
                            </a>
                            <div style={{ display: 'flex', gap: '0.5rem', width: '100%', marginTop: '1rem' }}>
                                <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => executeCheckout(selectedPlanId)} disabled={loading}>
                                    {loading ? <div className="spinner"></div> : "Verify"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
