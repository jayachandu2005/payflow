import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from || '/products';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const user = await login(email, password);
      navigate(user.role === 'admin' ? '/admin' : redirectTo);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container page" style={{ maxWidth: 480 }}>
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Sign In to PayFlow</h1>
        <p className="muted" style={{ fontSize: '0.9rem', marginBottom: 20 }}>
          Demo customer: <code>customer@payflow.dev</code> / <code>Customer@123</code>
          <br />
          Demo admin: <code>admin@payflow.dev</code> / <code>Admin@123</code>
        </p>

        {error && (
          <div className="alert alert-error" data-testid="login-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} data-testid="login-form">
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              data-testid="login-email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              data-testid="login-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={submitting}
            data-testid="login-submit"
          >
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="muted" style={{ marginTop: 18, fontSize: '0.9rem', textAlign: 'center' }}>
          New to PayFlow?{' '}
          <Link to="/register" style={{ color: '#818cf8' }}>
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
