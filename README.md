# PayFlow — Full-Stack Payment Gateway & End-to-End QA Automation Platform

PayFlow is a production-structured full-stack commerce and payment application built with **React + Vite**, **FastAPI**, **SQLAlchemy (PostgreSQL / SQLite)**, official **Stripe & Razorpay Sandbox SDKs**, and a reusable **Selenium + Pytest Page Object Model (POM)** automation framework with MP4 browser video recording and HTML reporting.

---

## Features

- **Customer Commerce Flow**: Home showcase, registration/login (JWT + bcrypt), searchable/filterable product catalog, product detail views, persistent shopping cart, validated checkout form, and payment method selection.
- **Genuine Payment Gateways (Sandbox/Test Mode)**:
  - **Razorpay Test Mode** (`razorpay` Python SDK + official `checkout.js`): triggers Razorpay's real hosted checkout modal and simulated ACS bank **3DS OTP page**.
  - **Stripe Sandbox** (`stripe` Python SDK + `@stripe/react-stripe-js`): supports both **Stripe Elements (3DS2 challenge modal)** and **Stripe Hosted Checkout Sessions**.
- **Authoritative Server Verification**:
  - Frontend never marks orders as paid from client callbacks or redirect parameters.
  - Backend queries `stripe.PaymentIntent.retrieve()` / `razorpay.payment.fetch()` and verifies cryptographic webhook signatures (`Stripe-Signature`, `X-Razorpay-Signature`).
  - Idempotency keys prevent duplicate payment creation; `WebhookEvent` deduplication prevents replay bugs.
  - Zero raw card numbers, CVVs, or OTP values are ever stored.
- **Dashboards**: Customer dashboard (spend metrics, orders, sanitized transaction ledger) and Admin operations dashboard (revenue, orders, payments, webhook audit log, product creation).
- **Automated Testing & Evidence**:
  - Python `requests` API integration suite covering auth, catalog, cart, checkout validation, idempotency, RBAC, and cryptographic webhook verification.
  - Selenium + Pytest POM E2E suite capturing PNG screenshots, genuine `.mp4` browser recordings, logs, and self-contained Pytest HTML reports.

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, Vite 6, React Router 7, `@stripe/react-stripe-js`, Razorpay `checkout.js`, Lucide Icons |
| Backend | Python 3.12/3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt |
| Database | PostgreSQL 16 (Docker/Production) with SQLite fallback for local development |
| Gateways | Official `stripe` SDK (v11), Official `razorpay` SDK (v1.4) |
| Automation | Selenium WebDriver 4, Pytest, `pytest-html`, Python `requests`, `imageio-ffmpeg` (MP4 recording) |
| DevOps | Docker, Multi-stage Dockerfiles, Nginx reverse proxy, Docker Compose, GitHub Actions CI |

---

## Architecture Overview

```
React SPA (Vite / Nginx)
   │
   ├── REST API (/api/*) ───────────────▶ FastAPI Backend
   │                                         ├── Auth & RBAC (JWT + bcrypt)
   │                                         ├── Cart / Orders / Admin
   │                                         ├── Payment Service (Idempotency + State Sync)
   │                                         ├── Stripe SDK ─────▶ Stripe Sandbox API
   │                                         ├── Razorpay SDK ───▶ Razorpay Test API
   │                                         └── SQLAlchemy ─────▶ PostgreSQL / SQLite
   │
   └── Official Gateway UIs
         ├── Stripe Elements / 3DS2 Iframe (hooks.stripe.com)
         └── Razorpay Checkout & Bank OTP Window (api.razorpay.com)
```

---

## Folder Structure

```text
d:\payment
├── backend/
│   ├── app/
│   │   ├── gateways/          # Stripe & Razorpay official SDK adapters
│   │   ├── routers/           # auth, products, cart, orders, payments, webhooks, admin
│   │   ├── services/          # Authoritative verification & order sync
│   │   ├── config.py          # Pydantic environment settings
│   │   ├── database.py        # SQLAlchemy engine & session management
│   │   ├── main.py            # FastAPI app & health check
│   │   ├── models.py          # ORM tables (users, products, cart, orders, payments, tx, webhooks)
│   │   ├── schemas.py         # Request/response validation schemas
│   │   ├── security.py        # bcrypt, JWT, RBAC, payload sanitization
│   │   └── seed.py            # Demo catalog & demo accounts
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # Fetch API client & currency formatter
│   │   ├── components/        # Navbar
│   │   ├── context/           # AuthContext, CartContext
│   │   └── pages/             # All 13 application views
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.js
├── database/
│   ├── alembic.ini
│   ├── schema.sql
│   └── migrations/
├── automation/
│   ├── pages/                 # Selenium Page Object Model classes
│   ├── tests/                 # E2E positive & negative Selenium Pytest suites
│   ├── utils/                 # Logger, screenshot capture, MP4 video recorder
│   └── config.py
├── tests/                     # Python Requests API integration tests
├── docs/                      # Gateway sandbox scenario matrix
├── reports/                   # Generated Pytest HTML reports
├── screenshots/               # Captured step & failure PNG screenshots
├── recordings/                # Genuine browser MP4 video recordings
├── logs/                      # Backend & automation log files
├── .github/workflows/ci.yml   # GitHub Actions CI workflow
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 20+ & **npm**
- **Google Chrome** (or Microsoft Edge) for Selenium E2E tests
- **Docker Desktop** (optional, for containerized PostgreSQL + full-stack run)
- Official sandbox keys from **Stripe** and/or **Razorpay**

---

## Installation & Setup

### 1. Clone & Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your genuine sandbox API keys (never commit `.env`):
- **Razorpay Test Mode**: `RAZORPAY_KEY_ID=rzp_test_...`, `RAZORPAY_KEY_SECRET=...`
- **Stripe Sandbox**: `STRIPE_PUBLISHABLE_KEY=pk_test_...`, `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_WEBHOOK_SECRET=whsec_...`

### 2. Install Backend & Automation Dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Database Setup

By default, local development uses SQLite (`database/payflow.db`), which is initialized and seeded automatically on backend startup.
To run Alembic migrations explicitly:

```bash
alembic -c database/alembic.ini upgrade head
```

---

## Payment Gateway Sandbox Setup & Official Test Credentials

### Razorpay Test Mode (Supports Real Numeric OTP Page)
1. Create a free account at [Razorpay Dashboard](https://dashboard.razorpay.com/) and switch to **Test Mode**.
2. Generate Test API keys under **Account & Settings → API Keys**.
3. Official test card docs: https://razorpay.com/docs/payments/payments/test-card-details/
   - **Test Visa Card**: `4100 2800 0000 1007` (any future expiry, any 3-digit CVV)
   - **OTP Success**: Enter `123456` (4+ digits) on Razorpay's hosted bank OTP page
   - **OTP Failure**: Enter `123` (fewer than 4 digits)

### Stripe Sandbox (Supports Real 3DS2 Challenge Modal & Hosted Checkout)
1. Create a free account at [Stripe Dashboard](https://dashboard.stripe.com/) and enable **Test Mode**.
2. Copy `pk_test_...` and `sk_test_...` from **Developers → API keys**.
3. Official test card docs: https://docs.stripe.com/testing
   - **3DS2 Success Challenge**: `4000 0025 0000 3155` (click **Complete** in Stripe's 3DS2 modal)
   - **3DS2 Authentication Fail**: `4000 0000 0000 3063` (click **Fail** in Stripe's 3DS2 modal)
   - **Declined Card**: `4000 0000 0000 0002`

---

## Running the Application Locally

### Start Backend (Terminal 1)

```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

API Docs (Swagger): `http://localhost:8000/docs`

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Application URL: `http://localhost:5173`

Seeded Demo Accounts:
- **Customer**: `customer@payflow.dev` / `Customer@123`
- **Admin**: `admin@payflow.dev` / `Admin@123`

---

## Running with Docker Compose

Ensure Docker Desktop is running, then run:

```bash
docker compose up --build -d
```

- Frontend (Nginx): `http://localhost:3000`
- Backend API: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5432`

Stop containers:

```bash
docker compose down
```

---

## Running Tests & Generating Reports

### 1. Backend API Tests (Python Requests)

```bash
pytest tests -m api --html=reports/api_report.html --self-contained-html
```

### 2. Selenium End-to-End Tests (with Video Recording & Screenshots)

Ensure backend (`:8000`) and frontend (`:5173`) are running, then run:

```bash
pytest automation/tests -m e2e --html=reports/e2e_report.html --self-contained-html
```

To run only tests that do not require external gateway keys:

```bash
pytest automation/tests -m "e2e and not gateway_live" --html=reports/e2e_report.html --self-contained-html
```

### Accessing Evidence
- **HTML Reports**: `reports/api_report.html`, `reports/e2e_report.html`
- **Screenshots**: `screenshots/*.png`
- **MP4 Browser Videos**: `recordings/*.mp4`
- **Logs**: `logs/backend.log`, `logs/automation.log`

---

## Actual Verified Test Results (Current Submission State)

- **Backend API Integration Suite (`pytest tests -m api`)**: **14 passed, 0 failed** (`reports/api_report.html`), covering registration/login/JWT, RBAC (`403`), catalog/cart, checkout validation, anti-spoofing (`400` on mismatched `gateway_order_id`), order-cancel/payment sync, and Stripe & Razorpay HMAC webhook signature verification + deduplication.
- **Selenium E2E UI Suite (`pytest automation/tests/test_e2e_auth_and_catalog.py`)**: **3 passed, 0 failed** (`reports/e2e_report.html`), with PNG screenshots and playable H.264 MP4 recordings.
- **Razorpay Test Mode & Tunnel**: Razorpay Test Mode keys (`rzp_test_...`) and webhook secret configured in `.env`; FastAPI backend health (`razorpay_sandbox_configured: true`) and HTTPS ngrok tunnel verified, and genuine Razorpay Checkout order initiation demonstrated in `evidence/payflow_demo_walkthrough.mp4`.
- **Known Limitations**:
  - Live Selenium OTP completion tests (`test_complete_sandbox_payment_with_real_otp_or_3ds`, `test_failed_otp_or_3ds_authentication`, `test_user_cancels_payment_before_completion`) failed in `reports/live_gateway_report.html` due to headless DOM interaction timeouts prior to bank OTP submission and were halted under the submission time-box.
  - Stripe sandbox keys (`pk_test_` / `sk_test_`) are not populated in local `.env`.
  - Docker Desktop engine was stopped during verification (`docker compose config -q` passed).

---

## Known Limitations

- Live sandbox E2E payment tests (`@pytest.mark.gateway_live`) require valid `STRIPE_*` or `RAZORPAY_*` test keys in `.env` and outbound internet access. Without keys, the backend returns HTTP `503` explaining the missing configuration and live gateway E2E tests skip cleanly rather than faking success.
- Stripe's sandbox 3DS2 modal displays **Complete** / **Fail** challenge buttons rather than a numeric OTP field; Razorpay's test mode provides a numeric OTP input window. See [GATEWAY_SANDBOX_MATRIX.md](docs/GATEWAY_SANDBOX_MATRIX.md).

---

## Troubleshooting

- **Port 8000 or 5173 already in use**: Stop conflicting processes or adjust `FRONTEND_URL` / `E2E_BASE_URL`.
- **Gateway returns 503**: Verify `.env` contains real `sk_test_`/`pk_test_` or `rzp_test_` keys without `replace_with` placeholders, then restart the backend.
- **ChromeDriver version mismatch**: Selenium 4.27 includes Selenium Manager to auto-fetch matching drivers; ensure Chrome is up to date.
