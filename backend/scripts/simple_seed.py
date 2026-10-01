"""Simple seed script to initialize database with admin user."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session_maker
from app.models import User, UserRole
from app.services.auth_service import hash_password


async def create_simple_seed():
    """Create minimal seed data for Phase 1 testing."""
    async with async_session_maker() as session:
        # Check if admin user exists
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("Database already has data, skipping seed.")
            return

        print("Creating seed data...")

        # Create admin user
        admin = User(
            username="admin",
            email="admin@supermarket.com",
            full_name="System Administrator",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            max_discount_percent=100
        )
        session.add(admin)

        # Create cashier user
        cashier = User(
            username="cashier1",
            email="cashier@supermarket.com",
            full_name="John Cashier",
            password_hash=hash_password("cashier123"),
            role=UserRole.CASHIER,
            is_active=True,
            max_discount_percent=10
        )
        session.add(cashier)

        # Create manager user
        manager = User(
            username="manager1",
            email="manager@supermarket.com",
            full_name="Store Manager",
            password_hash=hash_password("manager123"),
            role=UserRole.MANAGER,
            is_active=True,
            max_discount_percent=50
        )
        session.add(manager)

        # Create inventory manager
        inventory = User(
            username="inventory1",
            email="inventory@supermarket.com",
            full_name="Inventory Manager",
            password_hash=hash_password("inventory123"),
            role=UserRole.INVENTORY_MANAGER,
            is_active=True,
            max_discount_percent=5
        )
        session.add(inventory)

        await session.commit()

        print("\n" + "="*50)
        print("✓ Seed data created successfully!")
        print("="*50)
        print("\nLogin Credentials:")
        print("-" * 50)
        print("Admin:       admin / admin123")
        print("Cashier:     cashier1 / cashier123")
        print("Manager:     manager1 / manager123")
        print("Inventory:   inventory1 / inventory123")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(create_simple_seed())