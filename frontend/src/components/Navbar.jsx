import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { CreditCard, LogOut, ShieldCheck, ShoppingCart, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="brand" data-testid="nav-brand">
          <span className="brand-badge">
            <CreditCard size={18} />
          </span>
          <span>PayFlow</span>
        </Link>

        <nav className="nav-links">
          <NavLink to="/" className="nav-link" data-testid="nav-home">
            Home
          </NavLink>
          <NavLink to="/products" className="nav-link" data-testid="nav-products">
            Products
          </NavLink>
          {user && (
            <>
              <NavLink to="/orders" className="nav-link" data-testid="nav-orders">
                Orders
              </NavLink>
              <NavLink to="/dashboard" className="nav-link" data-testid="nav-dashboard">
                Dashboard
              </NavLink>
            </>
          )}
          {user?.role === 'admin' && (
            <NavLink to="/admin" className="nav-link" data-testid="nav-admin">
              <ShieldCheck size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Admin
            </NavLink>
          )}
        </nav>

        <div className="nav-actions">
          <Link to="/cart" className="btn btn-secondary btn-sm" data-testid="nav-cart">
            <ShoppingCart size={16} />
            <span>Cart ({cart.item_count || 0})</span>
          </Link>

          {user ? (
            <>
              <span className="muted" style={{ fontSize: '0.85rem' }} data-testid="nav-user-email">
                <User size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                {user.full_name}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleLogout}
                data-testid="nav-logout"
              >
                <LogOut size={15} />
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-secondary btn-sm" data-testid="nav-login">
                Login
              </Link>
              <Link to="/register" className="btn btn-primary btn-sm" data-testid="nav-register">
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
