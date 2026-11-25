import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import { useAuth } from './AuthContext';

const CartContext = createContext(null);

const EMPTY_CART = {
  items: [],
  item_count: 0,
  subtotal_cents: 0,
  tax_cents: 0,
  total_cents: 0,
  currency: 'USD',
};

export function CartProvider({ children }) {
  const { user } = useAuth();
  const [cart, setCart] = useState(EMPTY_CART);

  const refreshCart = useCallback(async () => {
    if (!user) {
      setCart(EMPTY_CART);
      return;
    }
    try {
      const data = await apiRequest('/api/cart');
      setCart(data);
    } catch {
      setCart(EMPTY_CART);
    }
  }, [user]);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const addItem = async (productId, quantity = 1) => {
    const data = await apiRequest('/api/cart/items', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, quantity }),
    });
    setCart(data);
    return data;
  };

  const updateItem = async (itemId, quantity) => {
    const data = await apiRequest(`/api/cart/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ quantity }),
    });
    setCart(data);
    return data;
  };

  const removeItem = async (itemId) => {
    const data = await apiRequest(`/api/cart/items/${itemId}`, {
      method: 'DELETE',
    });
    setCart(data);
    return data;
  };

  const clearCart = async () => {
    const data = await apiRequest('/api/cart', { method: 'DELETE' });
    setCart(data);
    return data;
  };

  return (
    <CartContext.Provider value={{ cart, refreshCart, addItem, updateItem, removeItem, clearCart }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  return useContext(CartContext);
}
