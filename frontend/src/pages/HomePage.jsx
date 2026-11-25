import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Lock, Shield, Zap } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';

export default function HomePage() {
  const [featured, setFeatured] = useState([]);
  const [gatewayConfig, setGatewayConfig] = useState(null);

  useEffect(() => {
    apiRequest('/api/products')
      .then((data) => setFeatured(data.slice(0, 3)))
      .catch(() => {});
    apiRequest('/api/payments/config')
      .then((cfg) => setGatewayConfig(cfg))
      .catch(() => {});
  }, []);

  return (
    <div className="container page">
      <section className="hero" data-testid="home-hero">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
          <span className="badge badge-info">Official Gateway Sandboxes</span>
          <span className="badge badge-success">3D Secure 2 &amp; OTP Ready</span>
          <span className="badge badge-warning">Zero Raw Card Storage</span>
        </div>
        <h1 style={{ fontSize: '2.4rem', margin: '0 0 12px', lineHeight: 1.15 }}>
          Enterprise Payment Commerce &amp; End-to-End 3DS Verification
        </h1>
        <p className="muted" style={{ maxWidth: 680, fontSize: '1.05rem', marginBottom: 24 }}>
          PayFlow integrates official Stripe and Razorpay sandbox SDKs with server-authoritative transaction
          verification, cryptographic webhook validation, and automated Selenium QA coverage.
        </p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link to="/products" className="btn btn-primary" data-testid="hero-browse-products">
            Browse Products <ArrowRight size={17} />
          </Link>
          <Link to="/register" className="btn btn-secondary" data-testid="hero-create-account">
            Create Customer Account
          </Link>
        </div>
      </section>

      <section className="grid-3" style={{ marginBottom: 36 }}>
        <div className="card">
          <Lock size={22} color="#22d3ee" />
          <h3 style={{ marginTop: 12, marginBottom: 6 }}>Authoritative Verification</h3>
          <p className="muted" style={{ margin: 0, fontSize: '0.92rem' }}>
            Orders are marked paid only after backend SDK queries and verified gateway webhooks confirm capture.
          </p>
        </div>
        <div className="card">
          <Shield size={22} color="#34d399" />
          <h3 style={{ marginTop: 12, marginBottom: 6 }}>Genuine 3DS / OTP Flows</h3>
          <p className="muted" style={{ margin: 0, fontSize: '0.92rem' }}>
            Hosted Stripe 3DS2 challenge modals and Razorpay ACS OTP screens — never simulated locally.
          </p>
        </div>
        <div className="card">
          <Zap size={22} color="#fbbf24" />
          <h3 style={{ marginTop: 12, marginBottom: 6 }}>Idempotent &amp; Audited</h3>
          <p className="muted" style={{ margin: 0, fontSize: '0.92rem' }}>
            Every payment attempt uses unique idempotency keys and writes sanitized ledger entries.
          </p>
        </div>
      </section>

      {gatewayConfig && (
        <section className="card" style={{ marginBottom: 36 }} data-testid="gateway-status-banner">
          <h3 style={{ marginTop: 0, marginBottom: 12 }}>Active Sandbox Gateway Integrations</h3>
          <div className="grid-2">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <CheckCircle2 size={18} color={gatewayConfig.razorpay_configured ? '#10b981' : '#f59e0b'} />
              <span>
                Razorpay Test Mode (OTP / 3DS):{' '}
                <strong>{gatewayConfig.razorpay_configured ? 'Configured & Ready' : 'Awaiting Keys in .env'}</strong>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <CheckCircle2 size={18} color={gatewayConfig.stripe_configured ? '#10b981' : '#f59e0b'} />
              <span>
                Stripe Sandbox (3DS2 / Checkout):{' '}
                <strong>{gatewayConfig.stripe_configured ? 'Configured & Ready' : 'Awaiting Keys in .env'}</strong>
              </span>
            </div>
          </div>
        </section>
      )}

      <section>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Featured Products</h2>
          <Link to="/products" className="nav-link">
            View all products →
          </Link>
        </div>
        <div className="grid-3">
          {featured.map((product) => (
            <div key={product.id} className="card" data-testid={`featured-product-${product.id}`}>
              <img src={product.image_url} alt={product.name} className="product-img" />
              <span className="badge badge-info" style={{ marginBottom: 8 }}>
                {product.category}
              </span>
              <h3 style={{ margin: '6px 0 8px' }}>{product.name}</h3>
              <p className="muted" style={{ fontSize: '0.88rem', minHeight: 48 }}>
                {product.description.slice(0, 100)}...
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 }}>
                <span className="price">{formatMoney(product.price_cents, product.currency)}</span>
                <Link to={`/products/${product.id}`} className="btn btn-primary btn-sm">
                  View Details
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
