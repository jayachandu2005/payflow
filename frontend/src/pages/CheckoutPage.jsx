import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CreditCard, Lock, ShieldCheck } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function CheckoutPage() {
  const { user } = useAuth();
  const { cart, refreshCart } = useCart();
  const navigate = useNavigate();

  const [config, setConfig] = useState(null);
  const [selectedKey, setSelectedKey] = useState('razorpay:razorpay_checkout');
  const [form, setForm] = useState({
    customer_name: user?.full_name || '',
    customer_email: user?.email || '',
    customer_phone: user?.phone || '+14155550101',
    shipping_address: '',
    shipping_city: '',
    shipping_postal_code: '',
    shipping_country: 'United States',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      setForm((prev) => ({
        ...prev,
        customer_name: prev.customer_name || user.full_name || '',
        customer_email: prev.customer_email || user.email || '',
        customer_phone: prev.customer_phone || user.phone || '+14155550101',
      }));
    }
  }, [user]);

  useEffect(() => {
    apiRequest('/api/payments/config')
      .then((cfg) => {
        setConfig(cfg);
        const firstConfigured = cfg.available_methods.find((m) => m.configured);
        if (firstConfigured) {
          setSelectedKey(`${firstConfigured.provider}:${firstConfigured.payment_method}`);
        }
      })
      .catch(() => {});
  }, []);

  if (!user) {
    return (
      <div className="container page">
        <div className="card">
          <h2>Please sign in to checkout</h2>
          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (cart.items.length === 0) {
    return (
      <div className="container page">
        <div className="card">
          <h2>Your cart is empty</h2>
          <p className="muted">Add at least one product before proceeding to checkout.</p>
          <Link to="/products" className="btn btn-primary">
            Browse Products
          </Link>
        </div>
      </div>
    );
  }

  const handleCheckoutSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const order = await apiRequest('/api/orders/checkout', {
        method: 'POST',
        body: JSON.stringify(form),
      });
      await refreshCart();
      const [provider, payment_method] = selectedKey.split(':');
      navigate(`/payment/process/${order.id}`, {
        state: { provider, payment_method, order },
      });
    } catch (err) {
      setError(err.message || 'Checkout validation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container page">
      <h1 style={{ marginTop: 0 }}>Checkout</h1>
      {error && (
        <div className="alert alert-error" data-testid="checkout-error">
          {error}
        </div>
      )}

      <form onSubmit={handleCheckoutSubmit} className="grid-2" style={{ gridTemplateColumns: '1.4fr 1fr' }} data-testid="checkout-form">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>1. Customer &amp; Shipping Information</h3>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="cust-name">
                Full Name
              </label>
              <input
                id="cust-name"
                className="input"
                value={form.customer_name}
                onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                required
                minLength={2}
                data-testid="checkout-name"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="cust-email">
                Email Address
              </label>
              <input
                id="cust-email"
                type="email"
                className="input"
                value={form.customer_email}
                onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
                required
                data-testid="checkout-email"
              />
            </div>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="cust-phone">
                Phone Number
              </label>
              <input
                id="cust-phone"
                className="input"
                value={form.customer_phone}
                onChange={(e) => setForm({ ...form, customer_phone: e.target.value })}
                required
                data-testid="checkout-phone"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="cust-country">
                Country
              </label>
              <input
                id="cust-country"
                className="input"
                value={form.shipping_country}
                onChange={(e) => setForm({ ...form, shipping_country: e.target.value })}
                required
                data-testid="checkout-country"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="cust-address">
              Street Address
            </label>
            <input
              id="cust-address"
              className="input"
              placeholder="221B Baker Street"
              value={form.shipping_address}
              onChange={(e) => setForm({ ...form, shipping_address: e.target.value })}
              required
              minLength={5}
              data-testid="checkout-address"
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="cust-city">
                City
              </label>
              <input
                id="cust-city"
                className="input"
                value={form.shipping_city}
                onChange={(e) => setForm({ ...form, shipping_city: e.target.value })}
                required
                data-testid="checkout-city"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="cust-postal">
                Postal Code
              </label>
              <input
                id="cust-postal"
                className="input"
                value={form.shipping_postal_code}
                onChange={(e) => setForm({ ...form, shipping_postal_code: e.target.value })}
                required
                data-testid="checkout-postal"
              />
            </div>
          </div>

          <h3 style={{ marginTop: 24 }}>2. Select Payment Method</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} data-testid="payment-method-list">
            {(config?.available_methods || []).map((method) => {
              const key = `${method.provider}:${method.payment_method}`;
              const active = selectedKey === key;
              return (
                <label
                  key={key}
                  data-testid={`method-${method.provider}-${method.payment_method}`}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12,
                    padding: 14,
                    borderRadius: 10,
                    border: `1px solid ${active ? '#6366f1' : 'var(--border)'}`,
                    background: active ? 'rgba(99, 102, 241, 0.12)' : '#0d1326',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    value={key}
                    checked={active}
                    onChange={() => setSelectedKey(key)}
                    style={{ marginTop: 4 }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <strong>{method.label}</strong>
                      <span className={`badge ${method.configured ? 'badge-success' : 'badge-warning'}`}>
                        {method.configured ? 'Sandbox Ready' : 'Not Configured'}
                      </span>
                    </div>
                    <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.84rem' }}>
                      {method.description}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="card" style={{ height: 'fit-content' }}>
          <h3 style={{ marginTop: 0 }}>Order Review</h3>
          {cart.items.map((item) => (
            <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
              <span>
                {item.product.name} × {item.quantity}
              </span>
              <span>{formatMoney(item.line_total_cents, cart.currency)}</span>
            </div>
          ))}
          <hr style={{ borderColor: 'var(--border)', margin: '14px 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="muted">Subtotal</span>
            <span>{formatMoney(cart.subtotal_cents, cart.currency)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="muted">Tax (8%)</span>
            <span>{formatMoney(cart.tax_cents, cart.currency)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.2rem', fontWeight: 700, margin: '14px 0 20px' }}>
            <span>Total</span>
            <span data-testid="checkout-total">{formatMoney(cart.total_cents, cart.currency)}</span>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={submitting}
            data-testid="checkout-submit"
          >
            <CreditCard size={17} />
            {submitting ? 'Creating Order...' : 'Continue to Payment'}
          </button>

          <p className="muted" style={{ fontSize: '0.8rem', marginTop: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Lock size={14} /> Card details &amp; OTP are handled exclusively by the official gateway iframe/page.
          </p>
          <p className="muted" style={{ fontSize: '0.8rem', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldCheck size={14} /> Never stores raw card numbers, CVV, or OTP.
          </p>
        </div>
      </form>
    </div>
  );
}
