"""Database seeding for initial demo catalog and accounts."""

from sqlalchemy.orm import Session

from .models import Product, User
from .security import hash_password

DEFAULT_PRODUCTS = [
    {
        "name": "PayFlow Hardware Security Key (FIDO2)",
        "slug": "payflow-fido2-security-key",
        "description": (
            "USB-C + NFC hardware security token supporting FIDO2, WebAuthn, and 3DS biometric passkeys "
            "for enterprise payment workflows."
        ),
        "price_cents": 4900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=800&q=80",
        "category": "Security Hardware",
        "stock": 120,
    },
    {
        "name": "Cloud POS Terminal Pro",
        "slug": "cloud-pos-terminal-pro",
        "description": (
            "Next-generation wireless countertop payment terminal with EMV chip, contactless NFC, "
            "and dual-band Wi-Fi synchronization."
        ),
        "price_cents": 19900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=800&q=80",
        "category": "POS Terminals",
        "stock": 45,
    },
    {
        "name": "Merchant Analytics Pro License (Annual)",
        "slug": "merchant-analytics-pro-annual",
        "description": (
            "Real-time settlement tracking, chargeback defense rules, and multi-currency reconciliation "
            "dashboard for scaling commerce teams."
        ),
        "price_cents": 9900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
        "category": "Software Subscriptions",
        "stock": 500,
    },
    {
        "name": "PCI-DSS Compliance Audit Toolkit",
        "slug": "pci-dss-compliance-toolkit",
        "description": (
            "Automated tokenization scanner, SAQ-A readiness checklist, and webhook cryptographic "
            "verification suite for payment engineers."
        ),
        "price_cents": 14900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80",
        "category": "Compliance & Security",
        "stock": 200,
    },
    {
        "name": "Smart NFC Tap-to-Pay Reader",
        "slug": "smart-nfc-tap-reader",
        "description": (
            "Pocket-sized Bluetooth contactless card reader engineered for mobile field sales, "
            "pop-up retail, and instant receipt generation."
        ),
        "price_cents": 7900,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1556742111-a301076d9d18?auto=format&fit=crop&w=800&q=80",
        "category": "POS Terminals",
        "stock": 85,
    },
    {
        "name": "Developer Sandbox Starter Kit",
        "slug": "developer-sandbox-starter-kit",
        "description": (
            "Test card deck, webhook tunnel reference guide, and automated QA integration templates "
            "for payment gateway engineering teams."
        ),
        "price_cents": 2500,
        "currency": "USD",
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80",
        "category": "Developer Tools",
        "stock": 300,
    },
]


def seed_database(db: Session) -> None:
    """Seed initial demo users and products idempotently."""
    # Seed products if empty
    if db.query(Product).count() == 0:
        for item in DEFAULT_PRODUCTS:
            db.add(Product(**item))

    # Seed default demo customer and admin if not present
    if not db.query(User).filter(User.email == "customer@payflow.dev").first():
        db.add(
            User(
                email="customer@payflow.dev",
                full_name="Alex Mercer",
                phone="+14155550101",
                password_hash=hash_password("Customer@123"),
                role="customer",
            )
        )

    if not db.query(User).filter(User.email == "admin@payflow.dev").first():
        db.add(
            User(
                email="admin@payflow.dev",
                full_name="PayFlow Admin",
                phone="+14155550199",
                password_hash=hash_password("Admin@123"),
                role="admin",
            )
        )

    db.commit()
