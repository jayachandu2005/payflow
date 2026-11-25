import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, ShoppingBag } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function ProductsPage() {
  const { user } = useAuth();
  const { addItem } = useCart();
  const navigate = useNavigate();

  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    if (category !== 'All') params.set('category', category);

    apiRequest(`/api/products?${params.toString()}`)
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [search, category]);

  const categories = ['All', 'Security Hardware', 'POS Terminals', 'Software Subscriptions', 'Compliance & Security', 'Developer Tools'];

  const handleAddToCart = async (productId) => {
    if (!user) {
      navigate('/login', { state: { from: '/products' } });
      return;
    }
    try {
      await addItem(productId, 1);
      setFeedback('Product added to cart.');
      setTimeout(() => setFeedback(''), 2500);
    } catch (err) {
      setFeedback(err.message);
    }
  };

  return (
    <div className="container page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Product Catalog</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            Select hardware, licenses, or sandbox toolkits to test end-to-end payment flows.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: 13, color: '#94a3b8' }} />
            <input
              type="text"
              className="input"
              style={{ paddingLeft: 36, width: 220 }}
              placeholder="Search products..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="products-search"
            />
          </div>
          <select
            className="select"
            style={{ width: 200 }}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            data-testid="products-category"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {feedback && (
        <div className="alert alert-success" data-testid="catalog-feedback">
          {feedback}
        </div>
      )}

      {loading ? (
        <p className="muted">Loading products...</p>
      ) : products.length === 0 ? (
        <div className="card">No products match your search criteria.</div>
      ) : (
        <div className="grid-3">
          {products.map((product) => (
            <div key={product.id} className="card" data-testid={`product-card-${product.id}`}>
              <img src={product.image_url} alt={product.name} className="product-img" />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span className="badge badge-info">{product.category}</span>
                <span className="muted" style={{ fontSize: '0.82rem' }}>
                  Stock: {product.stock}
                </span>
              </div>
              <h3 style={{ margin: '6px 0 8px' }}>
                <Link
                  to={`/products/${product.id}`}
                  style={{ display: 'block' }}
                  data-testid={`product-link-${product.id}`}
                >
                  {product.name}
                </Link>
              </h3>
              <p className="muted" style={{ fontSize: '0.88rem', minHeight: 54 }}>
                {product.description}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, gap: 8 }}>
                <span className="price">{formatMoney(product.price_cents, product.currency)}</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Link
                    to={`/products/${product.id}`}
                    className="btn btn-secondary btn-sm"
                    data-testid={`product-details-${product.id}`}
                  >
                    Details
                  </Link>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={product.stock <= 0}
                    onClick={() => handleAddToCart(product.id)}
                    data-testid={`add-to-cart-${product.id}`}
                  >
                    <ShoppingBag size={14} /> Add
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
