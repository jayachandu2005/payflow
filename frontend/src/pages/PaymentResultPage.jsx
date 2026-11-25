import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Clock, RefreshCw, XCircle } from 'lucide-react';
import { apiRequest, formatMoney } from '../api/client';

export default function PaymentResultPage() {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();

  const paymentId = searchParams.get('payment_id');
  const rzpPaymentId = searchParams.get('rzp_payment_id');
  const rzpOrderId = searchParams.get('rzp_order_id');
  const rzpSignature = searchParams.get('rzp_signature');
  const sessionId = searchParams.get('session_id');
  const piId = searchParams.get('pi');
  const cancelledFlag = searchParams.get('cancelled') === '1';

  const [result, setResult] = useState(null);
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const verify = async () => {
    setLoading(true);
    setError('');
    try {
      if (paymentId) {
        if (cancelledFlag && !rzpPaymentId && !sessionId) {
          try {
            const cancelledRes = await apiRequest('/api/payments/cancel', {
              method: 'POST',
              body: JSON.stringify({ payment_id: Number(paymentId), reason: 'Cancelled at gateway checkout' }),
            });
            setResult(cancelledRes);
            setOrder(cancelledRes.order);
            setLoading(false);
            return;
          } catch {
            // Fall through to authoritative verify
          }
        }

        const verified = await apiRequest('/api/payments/verify', {
          method: 'POST',
          body: JSON.stringify({
            payment_id: Number(paymentId),
            gateway_payment_id: rzpPaymentId || piId || null,
            gateway_order_id: rzpOrderId || sessionId || null,
            gateway_signature: rzpSignature || null,
          }),
        });
        setResult(verified);
        setOrder(verified.order);
      } else {
        const fetchedOrder = await apiRequest(`/api/orders/${orderId}`);
        setOrder(fetchedOrder);
      }
    } catch (err) {
      setError(err.message || 'Unable to verify payment status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    verify();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId, paymentId]);

  const paymentStatus = result?.payment?.status || order?.payments?.[0]?.status || 'pending';

  const renderStatusBanner = () => {
    if (paymentStatus === 'succeeded' || order?.status === 'paid') {
      return (
        <div style={{ textAlign: 'center', padding: '16px 0' }} data-testid="result-status-success">
          <CheckCircle2 size={54} color="#10b981" />
          <h1 style={{ margin: '12px 0 6px', color: '#34d399' }}>Payment Successful</h1>
          <p className="muted">
            Authoritatively verified by the backend with {result?.payment?.provider?.toUpperCase() || 'the payment gateway'}.
          </p>
        </div>
      );
    }
    if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
      return (
        <div style={{ textAlign: 'center', padding: '16px 0' }} data-testid="result-status-failed">
          <XCircle size={54} color="#ef4444" />
          <h1 style={{ margin: '12px 0 6px', color: '#f87171' }}>
            {paymentStatus === 'cancelled' ? 'Payment Cancelled' : 'Payment Failed'}
          </h1>
          <p className="muted">{result?.payment?.failure_reason || result?.message || 'Transaction was not completed.'}</p>
        </div>
      );
    }
    return (
      <div style={{ textAlign: 'center', padding: '16px 0' }} data-testid="result-status-pending">
        <Clock size={54} color="#f59e0b" />
        <h1 style={{ margin: '12px 0 6px', color: '#fbbf24' }}>Payment Pending</h1>
        <p className="muted">{result?.message || 'Awaiting final confirmation from the payment gateway.'}</p>
      </div>
    );
  };

  return (
    <div className="container page" style={{ maxWidth: 740 }}>
      <div className="card" data-testid="payment-result-card">
        {loading ? (
          <p className="muted" style={{ textAlign: 'center', padding: 32 }}>
            Verifying payment status directly with payment gateway API...
          </p>
        ) : error ? (
          <div className="alert alert-error" data-testid="result-error">
            {error}
          </div>
        ) : (
          <>
            {renderStatusBanner()}

            {order && (
              <div style={{ background: '#0d1326', borderRadius: 10, padding: 18, marginTop: 18, border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span className="muted">Order Number</span>
                  <strong data-testid="result-order-number">{order.order_number}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span className="muted">Order Status</span>
                  <span className="badge badge-info" data-testid="result-order-status">
                    {order.status}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span className="muted">Order Total</span>
                  <strong>{formatMoney(order.total_cents, order.currency)}</strong>
                </div>
                {result?.payment?.gateway_payment_id && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="muted">Gateway Payment ID</span>
                    <code data-testid="result-gateway-payment-id">{result.payment.gateway_payment_id}</code>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 24, flexWrap: 'wrap' }}>
              <button type="button" className="btn btn-secondary" onClick={verify} data-testid="result-reverify-btn">
                <RefreshCw size={15} /> Re-verify with Gateway
              </button>
              {order && order.status !== 'paid' && (
                <Link to={`/payment/process/${order.id}`} className="btn btn-primary" data-testid="result-retry-btn">
                  Retry Payment
                </Link>
              )}
              <Link to="/orders" className="btn btn-primary" data-testid="result-view-orders">
                View Order History
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
