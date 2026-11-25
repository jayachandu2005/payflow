import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ShoppingCart } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { addItem } = useCart();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState('');
  const [added, setAdded] = useState(false);

  useEffect(() => {
    apiRequest(`/api/products/${id}`)
      .then(setProduct)
      .catch((err) => setError(err.message));
  }, [id]);

  const handleAdd = async () => {
    if (!user) {
      navigate('/login', { state: { from: `/products/${id}` } });
      return;
    }
    setError('');
    try {
      await addItem(product.id, Number(quantity));
      setAdded(true);
    } catch (err) {
      setError(err.message);
    }
  };

  if (error && !product) {
    return (
      <div className="container page">
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="container page">
        <p className="muted">Loading product details...</p>
      </div>
    );
  }

  return (
    <div className="container page">
      <Link to="/products" className="btn btn-secondary btn-sm" style={{ marginBottom: 20 }}>
        <ArrowLeft size={15} /> Back to Products
      </Link>

      <div className="card grid-2" data-testid="product-detail-card">
        <div>
          <img
            src={product.image_url}
            alt={product.name}
            style={{ width: '100%', height: 340, objectFit: 'cover', borderRadius: 12 }}
          />
        </div>
        <div>
          <span className="badge badge-info">{product.category}</span>
          <h1 style={{ margin: '12px 0' }} data-testid="product-detail-title">
            {product.name}
          </h1>
          <p className="price" style={{ fontSize: '1.8rem', margin: '8px 0 16px' }} data-testid="product-detail-price">
            {formatMoney(product.price_cents, product.currency)}
          </p>
          <p className="muted" style={{ marginBottom: 20 }}>
            {product.description}
          </p>
          <p style={{ marginBottom: 20 }}>
            Availability: <strong>{product.stock > 0 ? `${product.stock} units in stock` : 'Out of stock'}</strong>
          </p>

          {error && <div className="alert alert-error">{error}</div>}
          {added && (
            <div className="alert alert-success" data-testid="detail-added-alert">
              Added to cart!{' '}
              <Link to="/cart" style={{ textDecoration: 'underline', fontWeight: 600 }}>
                Go to Shopping Cart →
              </Link>
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="number"
              min={1}
              max={Math.max(1, product.stock)}
              className="input"
              style={{ width: 95 }}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
              data-testid="detail-quantity"
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={product.stock <= 0}
              onClick={handleAdd}
              data-testid="detail-add-to-cart"
            >
              <ShoppingCart size={16} /> Add to Cart
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={async () => {
                await handleAdd();
                if (user) navigate('/cart');
              }}
              data-testid="detail-buy-now"
            >
              Buy Now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
