import React, { useEffect, useState } from 'react';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [payments, setPayments] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [newProduct, setNewProduct] = useState({
    name: '',
    slug: '',
    description: '',
    price_cents: 4900,
    category: 'Security Hardware',
    image_url: 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=800&q=80',
    stock: 25,
  });
  const [msg, setMsg] = useState('');

  const loadData = async () => {
    try {
      const [s, o, p, w] = await Promise.all([
        apiRequest('/api/admin/stats'),
        apiRequest('/api/admin/orders'),
        apiRequest('/api/admin/payments'),
        apiRequest('/api/admin/webhooks'),
      ]);
      setStats(s);
      setOrders(o);
      setPayments(p);
      setWebhooks(w);
    } catch {
      // handled by role guard
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      loadData();
    }
  }, [user]);

  if (!user || user.role !== 'admin') {
    return (
      <div className="container page">
        <div className="alert alert-error">Administrator privileges are required to access this page.</div>
      </div>
    );
  }

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setMsg('');
    try {
      await apiRequest('/api/products', {
        method: 'POST',
        body: JSON.stringify({ ...newProduct, price_cents: Number(newProduct.price_cents), stock: Number(newProduct.stock) }),
      });
      setMsg('Product created successfully.');
      loadData();
    } catch (err) {
      setMsg(err.message);
    }
  };

  return (
    <div className="container page" data-testid="admin-dashboard">
      <h1 style={{ marginTop: 0 }}>Admin Operations Dashboard</h1>

      {stats && (
        <div className="grid-4" style={{ marginBottom: 24 }}>
          <div className="card">
            <div className="muted">Verified Revenue</div>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#34d399' }}>
              {formatMoney(stats.total_revenue_cents, 'USD')}
            </div>
          </div>
          <div className="card">
            <div className="muted">Orders (Paid / Total)</div>
            <div style={{ fontSize: '1.7rem', fontWeight: 700 }}>
              {stats.paid_orders} / {stats.total_orders}
            </div>
          </div>
          <div className="card">
            <div className="muted">Failed Orders</div>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#f87171' }}>{stats.failed_orders}</div>
          </div>
          <div className="card">
            <div className="muted">Webhooks Logged</div>
            <div style={{ fontSize: '1.7rem', fontWeight: 700 }}>{stats.total_webhooks}</div>
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>Create Catalog Product</h3>
        {msg && <div className="alert alert-info">{msg}</div>}
        <form onSubmit={handleCreateProduct} className="grid-3">
          <input
            className="input"
            placeholder="Product Name"
            value={newProduct.name}
            onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="slug-like-this"
            value={newProduct.slug}
            onChange={(e) => setNewProduct({ ...newProduct, slug: e.target.value })}
            required
          />
          <input
            className="input"
            type="number"
            placeholder="Price in cents"
            value={newProduct.price_cents}
            onChange={(e) => setNewProduct({ ...newProduct, price_cents: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Category"
            value={newProduct.category}
            onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Description (min 10 chars)"
            value={newProduct.description}
            onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
            required
          />
          <button type="submit" className="btn btn-primary">
            Add Product
          </button>
        </form>
      </div>

      <div className="card table-wrap" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>Recent Payments</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Order ID</th>
              <th>Provider</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Gateway Ref</th>
            </tr>
          </thead>
          <tbody>
            {payments.slice(0, 15).map((p) => (
              <tr key={p.id}>
                <td>#{p.id}</td>
                <td>#{p.order_id}</td>
                <td>{p.provider}</td>
                <td>{formatMoney(p.amount_cents, p.currency)}</td>
                <td>
                  <span className="badge badge-info">{p.status}</span>
                </td>
                <td>
                  <code>{p.gateway_payment_id || p.gateway_order_id || '-'}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card table-wrap" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>All Orders</h3>
        <table>
          <thead>
            <tr>
              <th>Order #</th>
              <th>Customer</th>
              <th>Total</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.slice(0, 15).map((o) => (
              <tr key={o.id}>
                <td>{o.order_number}</td>
                <td>{o.customer_email}</td>
                <td>{formatMoney(o.total_cents, o.currency)}</td>
                <td>
                  <span className="badge badge-info">{o.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card table-wrap">
        <h3 style={{ marginTop: 0 }}>Webhook Events</h3>
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Event ID</th>
              <th>Type</th>
              <th>Signature Valid</th>
              <th>Processed</th>
            </tr>
          </thead>
          <tbody>
            {webhooks.map((w) => (
              <tr key={w.id}>
                <td>{w.provider}</td>
                <td>
                  <code>{w.event_id}</code>
                </td>
                <td>{w.event_type}</td>
                <td>{w.signature_valid ? 'Yes' : 'No'}</td>
                <td>{w.processed ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
