import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';

export default function OrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiRequest(`/api/orders/${id}`)
      .then(setOrder)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <div className="container page">
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }
  if (!order) {
    return (
      <div className="container page">
        <p className="muted">Loading order details...</p>
      </div>
    );
  }

  return (
    <div className="container page">
      <Link to="/orders" className="btn btn-secondary btn-sm" style={{ marginBottom: 20 }}>
        <ArrowLeft size={15} /> Back to Order History
      </Link>

      <div className="card" style={{ marginBottom: 20 }} data-testid="order-detail-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ margin: 0 }}>{order.order_number}</h1>
            <p className="muted" style={{ margin: '4px 0 0' }}>
              Placed on {new Date(order.created_at).toLocaleString()}
            </p>
          </div>
          <span className="badge badge-info" data-testid="order-detail-status">
            {order.status}
          </span>
        </div>

        <hr style={{ borderColor: 'var(--border)', margin: '18px 0' }} />

        <div className="grid-2">
          <div>
            <h3>Shipping &amp; Customer</h3>
            <p className="muted" style={{ margin: 0 }}>
              {order.customer_name} ({order.customer_email})
              <br />
              {order.customer_phone}
              <br />
              {order.shipping_address}, {order.shipping_city}, {order.shipping_postal_code}, {order.shipping_country}
            </p>
          </div>
          <div>
            <h3>Totals</h3>
            <p style={{ margin: 0 }}>
              Subtotal: {formatMoney(order.subtotal_cents, order.currency)}
              <br />
              Tax: {formatMoney(order.tax_cents, order.currency)}
              <br />
              <strong>Total: {formatMoney(order.total_cents, order.currency)}</strong>
            </p>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Items</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit Price</th>
              <th>Qty</th>
              <th>Line Total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item) => (
              <tr key={item.id}>
                <td>{item.product_name}</td>
                <td>{formatMoney(item.unit_price_cents, order.currency)}</td>
                <td>{item.quantity}</td>
                <td>{formatMoney(item.line_total_cents, order.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Payment Attempts</h3>
        {order.payments.length === 0 ? (
          <p className="muted">No payment attempts yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Method</th>
                  <th>Gateway Order ID</th>
                  <th>Gateway Payment ID</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {order.payments.map((p) => (
                  <tr key={p.id}>
                    <td>{p.provider}</td>
                    <td>{p.payment_method}</td>
                    <td>
                      <code>{p.gateway_order_id || '-'}</code>
                    </td>
                    <td>
                      <code>{p.gateway_payment_id || '-'}</code>
                    </td>
                    <td>
                      <span className="badge badge-info">{p.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
