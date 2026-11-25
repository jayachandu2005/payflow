import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function UserDashboardPage() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    if (!user) return;
    apiRequest('/api/orders').then(setOrders).catch(() => {});
    apiRequest('/api/payments/transactions').then(setTransactions).catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="container page">
        <div className="card">
          <h2>Sign in to view your dashboard</h2>
          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  const paidOrders = orders.filter((o) => o.status === 'paid');
  const totalSpentCents = paidOrders.reduce((acc, o) => acc + o.total_cents, 0);

  return (
    <div className="container page" data-testid="user-dashboard">
      <h1 style={{ marginTop: 0 }}>Customer Dashboard</h1>
      <p className="muted">
        Welcome back, <strong>{user.full_name}</strong> ({user.email})
      </p>

      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="muted" style={{ fontSize: '0.82rem' }}>
            Total Orders
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>{orders.length}</div>
        </div>
        <div className="card">
          <div className="muted" style={{ fontSize: '0.82rem' }}>
            Paid Orders
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#34d399' }}>{paidOrders.length}</div>
        </div>
        <div className="card">
          <div className="muted" style={{ fontSize: '0.82rem' }}>
            Total Verified Spend
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>{formatMoney(totalSpentCents, 'USD')}</div>
        </div>
        <div className="card">
          <div className="muted" style={{ fontSize: '0.82rem' }}>
            Ledger Events
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>{transactions.length}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Recent Orders</h3>
          {orders.slice(0, 5).map((o) => (
            <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <Link to={`/orders/${o.id}`}>{o.order_number}</Link>
              <span>
                {formatMoney(o.total_cents, o.currency)} — <strong>{o.status}</strong>
              </span>
            </div>
          ))}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Recent Transaction Activity</h3>
          {transactions.slice(0, 5).map((tx) => (
            <div key={tx.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <span>
                {tx.transaction_type} ({tx.status})
              </span>
              <code>{tx.gateway_reference || '-'}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
