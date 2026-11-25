# PayFlow Payment Test Scenario Matrix

This document details every payment scenario supported by PayFlow across **Razorpay Test Mode** and **Stripe Sandbox**, including exact official test behavior and any sandbox limitations.

| # | Scenario | Razorpay Test Mode | Stripe Sandbox | Notes |
|---|----------|--------------------|----------------|-------|
| 1 | Successful payment | Supported (`4100 2800 0000 1007` + OTP `123456`) | Supported (`4000 0025 0000 3155` + Complete 3DS2) | Verified server-side via official SDK before setting `order.status = 'paid'`. |
| 2 | Failed / declined payment | Supported (OTP `< 4` digits or bank fail button) | Supported (`4000 0000 0000 0002` card declined) | Backend records `payment.status = 'failed'` and `failure_reason`. |
| 3 | Incorrect test authentication | Supported (enter OTP `123` on Razorpay mock ACS page) | Supported (`4000 0000 0000 3063` + Fail Authentication) | Fails at gateway ACS/3DS challenge; order status syncs to `failed`. |
| 4 | Cancelled payment | Supported (dismiss modal or click Cancel Payment) | Supported (click Cancel Payment / expire Checkout Session) | Syncs `payment.status = 'cancelled'` and `order.status = 'cancelled'`. |
| 5 | Pending payment | Supported (`created` / `authorized` before capture) | Supported (`processing` PaymentIntent or `requires_action`) | UI renders `Payment Pending` and allows authoritative re-verification. |
| 6 | 3D Secure / OTP authentication | **Real numeric OTP input** on Razorpay's hosted mock ACS page | **Real 3DS2 challenge modal** (`hooks.stripe.com`) with Complete/Fail buttons | Stripe's sandbox uses Complete/Fail challenge buttons rather than numeric OTP digits; Razorpay provides an actual numeric OTP input field. |
| 7 | Duplicate payment request | Supported via unique `idempotency_key` in `payments` table | Supported via DB `idempotency_key` + Stripe SDK `idempotency_key` | Reusing the same `idempotency_key` returns the original Payment without duplicate gateway calls. |
| 8 | Webhook processing | Supported (`POST /api/webhooks/razorpay`) with `X-Razorpay-Signature` HMAC | Supported (`POST /api/webhooks/stripe`) with `Stripe-Signature` | Invalid signatures return `400`; duplicate `event_id` deliveries are safely deduplicated. |
| 9 | Payment status verification | `POST /api/payments/verify` -> HMAC verify + `client.payment.fetch()` | `POST /api/payments/verify` -> `payment_intents.retrieve()` / `sessions.retrieve()` | Frontend never trusts query params or client state alone. |
| 10 | Order status synchronization | Atomic state transition (`pending` -> `payment_initiated` -> `paid`/`failed`/`cancelled`) | Atomic state transition (`pending` -> `payment_initiated` -> `paid`/`failed`/`cancelled`) | Stock decrements once only when transitioning to `paid`. |
