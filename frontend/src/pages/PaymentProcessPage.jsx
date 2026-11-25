import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { CardElement, Elements, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import { AlertTriangle, CreditCard, Lock, ShieldCheck } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';

function StripeCardForm({ order, payment, gatewayPayload, onCancel }) {
  const stripe = useStripe();
  const elements = useElements();
  const navigate = useNavigate();
  const [processing, setProcessing] = useState(false);
  const [cardError, setCardError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setProcessing(true);
    setCardError('');

    const cardElement = elements.getElement(CardElement);
    const { error, paymentIntent } = await stripe.confirmCardPayment(gatewayPayload.client_secret, {
      payment_method: {
        card: cardElement,
        billing_details: {
          name: order.customer_name,
          email: order.customer_email,
          phone: order.customer_phone,
        },
      },
    });

    if (error) {
      setCardError(error.message || 'Authentication or card authorization failed.');
      // Still verify authoritatively with backend so DB records real failed attempt
      navigate(`/payment/result/${order.id}?payment_id=${payment.id}&pi=${gatewayPayload.payment_intent_id}`);
      return;
    }

    navigate(
      `/payment/result/${order.id}?payment_id=${payment.id}&pi=${paymentIntent?.id || gatewayPayload.payment_intent_id}`
    );
  };

  return (
    <form onSubmit={handleSubmit} data-testid="stripe-card-form">
      <div className="form-group">
        <label className="form-label">Card Details (Official Stripe Elements — PCI-DSS Isolated)</label>
        <div className="stripe-element-box" data-testid="stripe-card-element">
          <CardElement
            options={{
              style: {
                base: {
                  color: '#f1f5f9',
                  fontSize: '16px',
                  '::placeholder': { color: '#64748b' },
                },
                invalid: { color: '#f87171' },
              },
            }}
          />
        </div>
      </div>

      {cardError && (
        <div className="alert alert-error" data-testid="stripe-card-error">
          {cardError}
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!stripe || processing}
          data-testid="stripe-pay-submit"
        >
          <Lock size={16} />
          {processing ? 'Processing & 3DS Challenge...' : `Pay ${formatMoney(order.total_cents, order.currency)}`}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={processing} data-testid="payment-cancel-btn">
          Cancel Payment
        </button>
      </div>
    </form>
  );
}

export default function PaymentProcessPage() {
  const { orderId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const initialProvider = location.state?.provider || 'razorpay';
  const initialMethod = location.state?.payment_method || 'razorpay_checkout';

  const [order, setOrder] = useState(location.state?.order || null);
  const [provider, setProvider] = useState(initialProvider);
  const [paymentMethod, setPaymentMethod] = useState(initialMethod);
  const [payment, setPayment] = useState(null);
  const [gatewayPayload, setGatewayPayload] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const initiatedRef = useRef(false);
  const attemptTokenRef = useRef(Math.random().toString(36).slice(2, 10));

  const stripePromise = useMemo(() => {
    if (gatewayPayload?.mode === 'stripe_elements' && gatewayPayload.publishable_key) {
      return loadStripe(gatewayPayload.publishable_key);
    }
    return null;
  }, [gatewayPayload]);

  const initiate = async (targetProvider, targetMethod) => {
    setLoading(true);
    setError('');
    try {
      const ord = order || (await apiRequest(`/api/orders/${orderId}`));
      setOrder(ord);

      const idemKey = `ord-${ord.id}-${targetProvider}-${targetMethod}-${attemptTokenRef.current}`;
      const res = await apiRequest('/api/payments/initiate', {
        method: 'POST',
        body: JSON.stringify({
          order_id: ord.id,
          provider: targetProvider,
          payment_method: targetMethod,
          idempotency_key: idemKey,
        }),
      });
      setPayment(res.payment);
      setGatewayPayload(res.gateway_payload);
    } catch (err) {
      setError(err.message || 'Failed to initiate payment with gateway.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initiatedRef.current) return;
    initiatedRef.current = true;
    initiate(provider, paymentMethod);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const handleCancel = async () => {
    if (payment) {
      try {
        await apiRequest('/api/payments/cancel', {
          method: 'POST',
          body: JSON.stringify({ payment_id: payment.id, reason: 'Cancelled by user on payment page' }),
        });
      } catch {
        // Proceed to result page to show authoritative state
      }
      navigate(`/payment/result/${orderId}?payment_id=${payment.id}&cancelled=1`);
    } else {
      navigate('/orders');
    }
  };

  const launchRazorpayCheckout = () => {
    if (!gatewayPayload || gatewayPayload.mode !== 'razorpay_checkout') return;
    if (!window.Razorpay) {
      setError('Razorpay Checkout script failed to load. Check internet connectivity.');
      return;
    }

    const rzp = new window.Razorpay({
      key: gatewayPayload.key_id,
      amount: gatewayPayload.amount,
      currency: gatewayPayload.currency,
      name: gatewayPayload.name,
      description: gatewayPayload.description,
      order_id: gatewayPayload.razorpay_order_id,
      prefill: gatewayPayload.prefill,
      notes: gatewayPayload.notes,
      handler: (response) => {
        const params = new URLSearchParams({
          payment_id: String(payment.id),
          rzp_payment_id: response.razorpay_payment_id || '',
          rzp_order_id: response.razorpay_order_id || '',
          rzp_signature: response.razorpay_signature || '',
        });
        navigate(`/payment/result/${orderId}?${params.toString()}`);
      },
      modal: {
        ondismiss: () => {
          handleCancel();
        },
      },
      theme: { color: '#4f46e5' },
    });

    rzp.on('payment.failed', (resp) => {
      const failPayId = resp?.error?.metadata?.payment_id || '';
      const params = new URLSearchParams({
        payment_id: String(payment.id),
        rzp_payment_id: failPayId,
      });
      navigate(`/payment/result/${orderId}?${params.toString()}`);
    });

    rzp.open();
  };

  return (
    <div className="container page" style={{ maxWidth: 960 }}>
      <h1 style={{ marginTop: 0 }}>Payment Processing</h1>

      {order && (
        <div className="card" style={{ marginBottom: 20 }} data-testid="payment-order-banner">
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                Order Number
              </div>
              <strong data-testid="payment-order-number">{order.order_number}</strong>
            </div>
            <div>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                Order Total
              </div>
              <strong>{formatMoney(order.total_cents, order.currency)}</strong>
            </div>
            <div>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                Gateway Provider
              </div>
              <span className="badge badge-info" data-testid="payment-provider-badge">
                {provider} ({paymentMethod})
              </span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert-error" data-testid="payment-init-error">
          <AlertTriangle size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} />
          {error}
          <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setProvider('stripe');
                setPaymentMethod('card');
                initiate('stripe', 'card');
              }}
            >
              Try Stripe Sandbox
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setProvider('razorpay');
                setPaymentMethod('razorpay_checkout');
                initiate('razorpay', 'razorpay_checkout');
              }}
            >
              Try Razorpay Sandbox
            </button>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card" data-testid="payment-gateway-panel">
          <h3 style={{ marginTop: 0 }}>Official Gateway Interface</h3>
          {loading ? (
            <p className="muted">Connecting to official gateway sandbox...</p>
          ) : gatewayPayload?.mode === 'stripe_elements' && stripePromise ? (
            <Elements stripe={stripePromise}>
              <StripeCardForm order={order} payment={payment} gatewayPayload={gatewayPayload} onCancel={handleCancel} />
            </Elements>
          ) : gatewayPayload?.mode === 'stripe_checkout' ? (
            <div data-testid="stripe-checkout-redirect-panel">
              <p className="muted">
                Your Stripe Hosted Checkout Session is ready. Click below to open Stripe&apos;s official hosted page
                and complete 3D Secure authentication.
              </p>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <a
                  href={gatewayPayload.checkout_url}
                  className="btn btn-primary"
                  data-testid="open-stripe-checkout"
                >
                  <CreditCard size={16} /> Open Official Stripe Checkout
                </a>
                <button type="button" className="btn btn-secondary" onClick={handleCancel} data-testid="payment-cancel-btn">
                  Cancel Payment
                </button>
              </div>
            </div>
          ) : gatewayPayload?.mode === 'razorpay_checkout' ? (
            <div data-testid="razorpay-checkout-panel">
              <p className="muted">
                Razorpay Order <code>{gatewayPayload.razorpay_order_id}</code> created for{' '}
                <strong>{formatMoney(gatewayPayload.amount, 'INR')}</strong>. Launch Razorpay&apos;s official
                checkout modal to enter test card details and complete the bank 3DS OTP page.
              </p>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={launchRazorpayCheckout}
                  data-testid="launch-razorpay-btn"
                >
                  <ShieldCheck size={16} /> Pay with Razorpay Sandbox
                </button>
                <button type="button" className="btn btn-secondary" onClick={handleCancel} data-testid="payment-cancel-btn">
                  Cancel Payment
                </button>
              </div>
            </div>
          ) : (
            <p className="muted">Select a configured gateway or verify `.env` sandbox keys.</p>
          )}
        </div>

        <div className="card" data-testid="sandbox-test-reference">
          <h3 style={{ marginTop: 0 }}>Official Sandbox Test Credentials</h3>
          <p className="muted" style={{ fontSize: '0.86rem' }}>
            Use only official provider sandbox cards on the gateway&apos;s hosted interface:
          </p>
          <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <strong>Razorpay Test Mode (Real OTP Page):</strong>
              <ul style={{ margin: '6px 0', paddingLeft: 18 }} className="muted">
                <li>
                  Visa Card: <code>4100 2800 0000 1007</code> (Future Expiry, any 3-digit CVV)
                </li>
                <li>
                  OTP Success: Enter any 4+ digit OTP (e.g. <code>123456</code>) on Razorpay&apos;s bank OTP page
                </li>
                <li>
                  OTP Failure: Enter fewer than 4 digits (e.g. <code>123</code>)
                </li>
              </ul>
            </div>
            <div>
              <strong>Stripe Test Mode (Real 3DS2 Modal):</strong>
              <ul style={{ margin: '6px 0', paddingLeft: 18 }} className="muted">
                <li>
                  3DS2 Success Challenge: <code>4000 0025 0000 3155</code> (or <code>4000 0000 0000 3220</code>)
                </li>
                <li>
                  3DS2 Auth Fail: <code>4000 0000 0000 3063</code>
                </li>
                <li>
                  Standard Decline: <code>4000 0000 0000 0002</code>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
