"""
Seed script for Mercury Marketplace.
Creates demo users, products, wallets, and sample orders.
Safe to run multiple times — skips if already seeded.
"""

import logging
import sys
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.database import SessionLocal, init_db
from app.models.audit import AuditLog
from app.models.escrow import Escrow, EscrowStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductType
from app.models.user import User, UserRole
from app.models.wallet import TransactionType, Wallet, WalletTransaction

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def is_seeded(db: Session) -> bool:
    return db.query(User).filter(User.email == "admin@mercury.com").first() is not None


def reset_products(db: Session) -> None:
    """Restore seeded product inventory to original values (quantity and price)."""
    originals = {
        "Wireless Bluetooth Headphones":             (14,   89.99),
        "Full-Grain Leather Bifold Wallet":          (30,   45.00),
        "Artisan Ethiopian Coffee Blend — 500g":     (50,   24.99),
        "Classic Polarized Aviator Sunglasses":      (19,   55.00),
        "USB-C Hub 7-in-1 Pro":                      (24,   49.99),
        "TKL Mechanical Keyboard — Cherry MX Brown": (10,  129.99),
        "Python Programming Masterclass 2025":       (9999, 79.99),
        "React & TypeScript Masterclass":            (9999, 69.99),
    }
    for title, (qty, price) in originals.items():
        product = db.query(Product).filter(Product.title == title).first()
        if product:
            product.quantity = qty
            product.price = price
            product.is_active = True
    db.commit()


def seed(db: Session) -> None:
    logger.info("Seeding database with demo data...")

    # ── Users ──────────────────────────────────────────────────────────────────

    admin = User(
        email="admin@mercury.com",
        username="admin",
        hashed_password=get_password_hash("Admin123!"),
        full_name="Mercury Admin",
        bio="Platform administrator",
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )

    alice = User(
        email="alice@mercury.com",
        username="alice_shop",
        hashed_password=get_password_hash("Seller123!"),
        full_name="Alice Johnson",
        bio="Handcrafted accessories and lifestyle goods. All items made with care.",
        role=UserRole.seller,
        is_active=True,
        is_verified=True,
    )

    bob = User(
        email="bob@mercury.com",
        username="bobs_tech",
        hashed_password=get_password_hash("Seller123!"),
        full_name="Bob Smith",
        bio="Premium tech accessories and online courses for developers.",
        role=UserRole.seller,
        is_active=True,
        is_verified=True,
    )

    charlie = User(
        email="charlie@mercury.com",
        username="charlie_b",
        hashed_password=get_password_hash("Buyer123!"),
        full_name="Charlie Brown",
        role=UserRole.buyer,
        is_active=True,
        is_verified=True,
    )

    diana = User(
        email="diana@mercury.com",
        username="diana_m",
        hashed_password=get_password_hash("Buyer123!"),
        full_name="Diana Martinez",
        role=UserRole.buyer,
        is_active=True,
        is_verified=True,
    )

    for u in [admin, alice, bob, charlie, diana]:
        db.add(u)
    db.flush()

    # ── Wallets ─────────────────────────────────────────────────────────────────

    admin_wallet = Wallet(user_id=admin.id, balance=1000.00, pending_balance=0.0)
    alice_wallet = Wallet(user_id=alice.id, balance=50.00, pending_balance=175.50)
    bob_wallet = Wallet(user_id=bob.id, balance=30.00, pending_balance=89.99)
    charlie_wallet = Wallet(user_id=charlie.id, balance=610.01, pending_balance=0.0)
    diana_wallet = Wallet(user_id=diana.id, balance=395.00, pending_balance=0.0)

    for w in [admin_wallet, alice_wallet, bob_wallet, charlie_wallet, diana_wallet]:
        db.add(w)
    db.flush()

    # Wallet transactions — deposits
    for wallet, user, amount in [
        (charlie_wallet, charlie, 750.00),
        (diana_wallet, diana, 450.00),
        (admin_wallet, admin, 1000.00),
    ]:
        db.add(WalletTransaction(
            wallet_id=wallet.id,
            user_id=user.id,
            amount=amount,
            transaction_type=TransactionType.deposit,
            description="Initial account deposit",
            balance_after=amount,
            created_at=datetime.utcnow() - timedelta(days=20),
        ))

    # ── Products ────────────────────────────────────────────────────────────────

    alice_products = [
        Product(
            seller_id=alice.id,
            title="Wireless Bluetooth Headphones",
            description=(
                "Premium over-ear wireless headphones with active noise cancellation, "
                "30-hour battery life, and studio-quality sound. Foldable design with "
                "carry case included. Compatible with all Bluetooth 5.0 devices."
            ),
            price=89.99,
            quantity=14,
            product_type=ProductType.shippable,
            category="Electronics",
            image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
        ),
        Product(
            seller_id=alice.id,
            title="Full-Grain Leather Bifold Wallet",
            description=(
                "Handcrafted bifold wallet made from genuine full-grain leather. "
                "Features RFID-blocking lining, 8 card slots, 2 cash compartments, "
                "and a sleek minimalist design that fits comfortably in any pocket."
            ),
            price=45.00,
            quantity=30,
            product_type=ProductType.shippable,
            category="Accessories",
            image_url="https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&q=80",
        ),
        Product(
            seller_id=alice.id,
            title="Artisan Ethiopian Coffee Blend — 500g",
            description=(
                "Single-origin Ethiopian Yirgacheffe coffee beans, medium roast. "
                "Tasting notes of blueberry, jasmine, and dark chocolate. "
                "Sustainably sourced, fair-trade certified, and roasted to order."
            ),
            price=24.99,
            quantity=50,
            product_type=ProductType.shippable,
            category="Food & Beverage",
            image_url="https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&q=80",
        ),
        Product(
            seller_id=alice.id,
            title="Classic Polarized Aviator Sunglasses",
            description=(
                "Timeless aviator-style sunglasses with UV400-rated polarized lenses. "
                "Lightweight stainless steel frame, spring hinges, and anti-reflective coating. "
                "Available in gold/brown and silver/grey colorways."
            ),
            price=55.00,
            quantity=19,
            product_type=ProductType.shippable,
            category="Accessories",
            image_url="https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&q=80",
        ),
    ]

    bob_products = [
        Product(
            seller_id=bob.id,
            title="USB-C Hub 7-in-1 Pro",
            description=(
                "Expand your laptop's connectivity instantly. This compact hub adds "
                "4K@60Hz HDMI, 100W Power Delivery, 3× USB-A 3.0 ports, SD and "
                "microSD card readers — all from a single USB-C connection. "
                "Aluminium shell with active cooling."
            ),
            price=49.99,
            quantity=24,
            product_type=ProductType.shippable,
            category="Electronics",
            image_url="https://images.unsplash.com/photo-1625723524778-9bae4aaac3b3?w=600&q=80",
        ),
        Product(
            seller_id=bob.id,
            title="TKL Mechanical Keyboard — Cherry MX Brown",
            description=(
                "Tenkeyless mechanical keyboard with genuine Cherry MX Brown tactile switches. "
                "Per-key RGB backlighting, aircraft-grade aluminium top plate, "
                "USB-C braided detachable cable, and full N-key rollover. "
                "Perfect for programming and everyday productivity."
            ),
            price=129.99,
            quantity=10,
            product_type=ProductType.shippable,
            category="Electronics",
            image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80",
        ),
        Product(
            seller_id=bob.id,
            title="Python Programming Masterclass 2025",
            description=(
                "Complete Python 3 course — from beginner to professional. Covers "
                "data structures, OOP, async programming, testing, APIs, and data science. "
                "42 hours of HD video, 200+ coding exercises, real-world projects, "
                "and a certificate of completion. Instant digital delivery."
            ),
            price=79.99,
            quantity=9999,
            product_type=ProductType.digital,
            category="Education",
            image_url="https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=600&q=80",
        ),
        Product(
            seller_id=bob.id,
            title="React & TypeScript Masterclass",
            description=(
                "Build production-ready React 18 applications with TypeScript. "
                "Learn hooks, context API, React Router, Zustand, React Query, "
                "testing with Vitest, and deployment on Vercel. "
                "35 hours of content with hands-on projects. Instant digital delivery."
            ),
            price=69.99,
            quantity=9999,
            product_type=ProductType.digital,
            category="Education",
            image_url="https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=600&q=80",
        ),
    ]

    all_products = alice_products + bob_products
    for p in all_products:
        db.add(p)
    db.flush()

    p_headphones, p_wallet_item, p_coffee, p_sunglasses = alice_products
    p_hub, p_keyboard, p_python, p_react = bob_products

    # ── Orders ──────────────────────────────────────────────────────────────────

    # Order 1: Charlie bought headphones from Alice → COMPLETED
    order1_created = datetime.utcnow() - timedelta(days=12)
    order1 = Order(
        buyer_id=charlie.id,
        status=OrderStatus.completed,
        total_amount=89.99,
        shipping_address="123 Maple Street, Springfield, IL 62701, USA",
        tracking_number="1Z999AA10123456784",
        created_at=order1_created,
        updated_at=datetime.utcnow() - timedelta(days=5),
    )
    db.add(order1)
    db.flush()

    db.add(OrderItem(order_id=order1.id, product_id=p_headphones.id, seller_id=alice.id, quantity=1, unit_price=89.99))
    db.add(Escrow(order_id=order1.id, buyer_id=charlie.id, seller_id=alice.id, amount=89.99, status=EscrowStatus.released, created_at=order1_created, released_at=datetime.utcnow() - timedelta(days=5)))

    db.add(WalletTransaction(wallet_id=charlie_wallet.id, user_id=charlie.id, amount=-89.99, transaction_type=TransactionType.purchase, reference_id=order1.id, reference_type="order", description="Purchase — Order #1 (Wireless Bluetooth Headphones)", balance_after=660.01, created_at=order1_created))
    db.add(WalletTransaction(wallet_id=alice_wallet.id, user_id=alice.id, amount=89.99, transaction_type=TransactionType.escrow_release, reference_id=order1.id, reference_type="order", description="Sale proceeds — Order #1", balance_after=89.99, created_at=datetime.utcnow() - timedelta(days=5)))

    # Order 2: Charlie bought USB Hub from Bob → SHIPPED
    order2_created = datetime.utcnow() - timedelta(days=5)
    order2 = Order(
        buyer_id=charlie.id,
        status=OrderStatus.shipped,
        total_amount=49.99,
        shipping_address="123 Maple Street, Springfield, IL 62701, USA",
        tracking_number="9400111899223421001234",
        created_at=order2_created,
        updated_at=datetime.utcnow() - timedelta(days=2),
    )
    db.add(order2)
    db.flush()

    db.add(OrderItem(order_id=order2.id, product_id=p_hub.id, seller_id=bob.id, quantity=1, unit_price=49.99))
    db.add(Escrow(order_id=order2.id, buyer_id=charlie.id, seller_id=bob.id, amount=49.99, status=EscrowStatus.held, created_at=order2_created))
    db.add(WalletTransaction(wallet_id=charlie_wallet.id, user_id=charlie.id, amount=-49.99, transaction_type=TransactionType.purchase, reference_id=order2.id, reference_type="order", description="Purchase — Order #2 (USB-C Hub 7-in-1 Pro)", balance_after=610.02, created_at=order2_created))

    # Order 3: Diana bought sunglasses from Alice → PAID (awaiting shipment)
    order3_created = datetime.utcnow() - timedelta(days=1)
    order3 = Order(
        buyer_id=diana.id,
        status=OrderStatus.paid,
        total_amount=55.00,
        shipping_address="456 Oak Avenue, Portland, OR 97201, USA",
        created_at=order3_created,
        updated_at=order3_created,
    )
    db.add(order3)
    db.flush()

    db.add(OrderItem(order_id=order3.id, product_id=p_sunglasses.id, seller_id=alice.id, quantity=1, unit_price=55.00))
    db.add(Escrow(order_id=order3.id, buyer_id=diana.id, seller_id=alice.id, amount=55.00, status=EscrowStatus.held, created_at=order3_created))
    db.add(WalletTransaction(wallet_id=diana_wallet.id, user_id=diana.id, amount=-55.00, transaction_type=TransactionType.purchase, reference_id=order3.id, reference_type="order", description="Purchase — Order #3 (Classic Polarized Aviator Sunglasses)", balance_after=395.00, created_at=order3_created))

    # Adjust alice pending balance to reflect order 1 release + order 3 escrow pending
    # (alice_wallet.pending_balance was seeded to 175.50 total: 89.99 from order1 + 85.51 from prior demo)
    alice_wallet.pending_balance = 89.99
    alice_wallet.balance = 50.00

    db.add(AuditLog(
        user_id=admin.id,
        action="database_seeded",
        entity_type="system",
        details="Initial seed data loaded",
    ))

    db.commit()
    logger.info("✓ Seed complete!")
    logger.info("")
    logger.info("Demo accounts:")
    logger.info("  Admin  — admin@mercury.com   / Admin123!")
    logger.info("  Seller — alice@mercury.com   / Seller123!")
    logger.info("  Seller — bob@mercury.com     / Seller123!")
    logger.info("  Buyer  — charlie@mercury.com / Buyer123!")
    logger.info("  Buyer  — diana@mercury.com   / Buyer123!")


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        if is_seeded(db):
            logger.info("Database already seeded — resetting product inventory.")
            reset_products(db)
        else:
            seed(db)
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
