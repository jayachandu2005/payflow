import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';

function statusBadge(status) {
  if (status === 'paid' || status === 'succeeded') return 'badge-success';
  if (status === 'failed' || status === 'cancelled') return 'badge-danger';
  return 'badge-warning';
}

export default function OrdersPage() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    apiRequest('/api/orders')
      .then(setOrders)
      .catch(() => setOrders([]))
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) {
    return (
      <div className="container page">
        <div className="card">
          <h2>Sign in to view your orders</h2>
          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container page">
      <h1 style={{ marginTop: 0 }}>Order History</h1>
      {loading ? (
        <p className="muted">Loading orders...</p>
      ) : orders.length === 0 ? (
        <div className="card">
          <p className="muted">You have not placed any orders yet.</p>
          <Link to="/products" className="btn btn-primary">
            Shop Products
          </Link>
        </div>
      ) : (
        <div className="card table-wrap" data-testid="orders-table">
          <table>
            <thead>
              <tr>
                <th>Order #</th>
                <th>Date</th>
                <th>Items</th>
                <th>Total</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} data-testid={`order-row-${order.id}`}>
                  <td>
                    <strong>{order.order_number}</strong>
                  </td>
                  <td className="muted">{new Date(order.created_at).toLocaleString()}</td>
                  <td>{order.items.reduce((acc, i) => acc + i.quantity, 0)}</td>
                  <td>{formatMoney(order.total_cents, order.currency)}</td>
                  <td>
                    <span className={`badge ${statusBadge(order.status)}`} data-testid={`order-status-${order.id}`}>
                      {order.status}
                    </span>
                  </td>
                  <td style={{ display: 'flex', gap: 8 }}>
                    <Link to={`/orders/${order.id}`} className="btn btn-secondary btn-sm">
                      Details
                    </Link>
                    {order.status !== 'paid' && (
                      <Link to={`/payment/process/${order.id}`} className="btn btn-primary btn-sm">
                        Pay Now
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
