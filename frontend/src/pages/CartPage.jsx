import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Trash2 } from 'lucide-react';
import { formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function CartPage() {
  const { user } = useAuth();
  const { cart, updateItem, removeItem, clearCart } = useCart();
  const navigate = useNavigate();

  if (!user) {
    return (
      <div className="container page">
        <div className="card">
          <h2>Sign in to view your Shopping Cart</h2>
          <p className="muted">Your cart items are securely persisted to your account.</p>
          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>Shopping Cart</h1>
        {cart.items.length > 0 && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={clearCart} data-testid="cart-clear">
            Clear Cart
          </button>
        )}
      </div>

      {cart.items.length === 0 ? (
        <div className="card" data-testid="cart-empty">
          <p className="muted">Your shopping cart is currently empty.</p>
          <Link to="/products" className="btn btn-primary">
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="grid-2" style={{ gridTemplateColumns: '2fr 1fr' }}>
          <div className="card">
            {cart.items.map((item) => (
              <div
                key={item.id}
                data-testid={`cart-item-${item.id}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 16,
                  padding: '14px 0',
                  borderBottom: '1px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <img
                    src={item.product.image_url}
                    alt={item.product.name}
                    style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 8 }}
                  />
                  <div>
                    <div style={{ fontWeight: 600 }}>{item.product.name}</div>
                    <div className="muted" style={{ fontSize: '0.85rem' }}>
                      {formatMoney(item.product.price_cents, item.product.currency)} each
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    className="input"
                    style={{ width: 72, padding: '6px 10px' }}
                    value={item.quantity}
                    onChange={(e) => updateItem(item.id, Math.max(1, Number(e.target.value) || 1))}
                    data-testid={`cart-qty-${item.id}`}
                  />
                  <span style={{ minWidth: 80, textAlign: 'right', fontWeight: 600 }}>
                    {formatMoney(item.line_total_cents, cart.currency)}
                  </span>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => removeItem(item.id)}
                    data-testid={`cart-remove-${item.id}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="card" style={{ height: 'fit-content' }} data-testid="cart-summary">
            <h3 style={{ marginTop: 0 }}>Order Summary</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span className="muted">Subtotal</span>
              <span>{formatMoney(cart.subtotal_cents, cart.currency)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span className="muted">Estimated Tax (8%)</span>
              <span>{formatMoney(cart.tax_cents, cart.currency)}</span>
            </div>
            <hr style={{ borderColor: 'var(--border)', margin: '14px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.15rem', fontWeight: 700, marginBottom: 20 }}>
              <span>Total</span>
              <span data-testid="cart-total">{formatMoney(cart.total_cents, cart.currency)}</span>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              style={{ width: '100%' }}
              onClick={() => navigate('/checkout')}
              data-testid="proceed-to-checkout"
            >
              Proceed to Checkout <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
