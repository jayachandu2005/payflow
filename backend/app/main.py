"""PayFlow FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import PROJECT_ROOT, get_settings
from .database import SessionLocal, engine, init_db
from .routers import admin, auth, cart, orders, payments, products, webhooks
from .seed import seed_database

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "backend.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("payflow")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize schema and seed catalog on application startup."""
    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    logger.info("PayFlow backend started successfully.")
    yield
    logger.info("PayFlow backend shutting down.")


settings = get_settings()
app = FastAPI(
    title="PayFlow Payment Gateway API",
    version="1.0.0",
    description="Full-stack payment gateway integration supporting official Stripe & Razorpay sandboxes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Verify API and database connectivity."""
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "stripe_sandbox_configured": settings.stripe_configured,
        "razorpay_sandbox_configured": settings.razorpay_configured,
    }
