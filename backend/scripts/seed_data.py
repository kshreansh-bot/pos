"""Seed script with demo data for development and testing."""
import asyncio
import secrets
from datetime import datetime, timedelta
from app.database import async_session_maker, init_db
from app.models import (
    User, UserRole, Category, Supplier, Product, StockBatch, Customer
)
from app.services.auth_service import hash_password


async def create_seed_data():
    """Create seed data for the application."""
    await init_db()

    async with async_session_maker() as session:
        # Check if data already exists
        result = await session.execute(sa.select(sa.func.count(User.id)))
        if result.scalar() > 0:
            print("Database already has data, skipping seed.")
            return

        print("Creating seed data...")

        # Create users
        users = [
            User(
                username="admin",
                email="admin@supermarket.com",
                full_name="System Administrator",
                password_hash=hash_password("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                max_discount_percent=100
            ),
            User(
                username="manager1",
                email="manager@supermarket.com",
                full_name="Store Manager",
                password_hash=hash_password("manager123"),
                role=UserRole.MANAGER,
                is_active=True,
                max_discount_percent=50
            ),
            User(
                username="cashier1",
                email="cashier1@supermarket.com",
                full_name="John Cashier",
                password_hash=hash_password("cashier123"),
                role=UserRole.CASHIER,
                is_active=True,
                max_discount_percent=10
            ),
            User(
                username="inventory1",
                email="inventory@supermarket.com",
                full_name="Inventory Manager",
                password_hash=hash_password("inventory123"),
                role=UserRole.INVENTORY_MANAGER,
                is_active=True,
                max_discount_percent=5
            ),
        ]
        for user in users:
            session.add(user)
        await session.flush()
        print(f"✓ Created {len(users)} users")

        # Create categories
        categories = [
            Category(name="Beverages", description="Drinks and beverages"),
            Category(name="Dairy", description="Milk, cheese, yogurt"),
            Category(name="Bakery", description="Bread and baked goods"),
            Category(name="Snacks", description="Chips, chocolates, cookies"),
            Category(name="Household", description="Cleaning and household items"),
            Category(name="Personal Care", description="Hygiene and personal care"),
            Category(name="Fresh Produce", description="Fruits and vegetables"),
            Category(name="Frozen Foods", description="Frozen meals and ice cream"),
        ]
        for cat in categories:
            session.add(cat)
        await session.flush()
        print(f"✓ Created {len(categories)} categories")

        # Create suppliers
        suppliers = [
            Supplier(
                name="Beverages Co.",
                contact_person="Bob Beverages",
                phone="555-0101",
                email="orders@beverages.co",
                gst_number="GST001"
            ),
            Supplier(
                name="Dairy Fresh Ltd.",
                contact_person="Alice Dairy",
                phone="555-0102",
                email="sales@dairyfresh.co",
                gst_number="GST002"
            ),
            Supplier(
                name="Snacks International",
                contact_person="Charlie Snacks",
                phone="555-0103",
                email="bulk@snacksintl.co",
                gst_number="GST003"
            ),
        ]
        for sup in suppliers:
            session.add(sup)
        await session.flush()
        print(f"✓ Created {len(suppliers)} suppliers")

        # Create products (50+ as required)
        products_data = [
            # Beverages
            ("Coca Cola 500ml", "8901234567890", 0, 0, 199, 120, 150, 18),
            ("Pepsi 500ml", "8901234567891", 0, 0, 199, 120, 120, 18),
            ("Orange Juice 1L", "8901234567892", 0, 0, 349, 210, 80, 12),
            ("Mineral Water 1L", "8901234567893", 0, 0, 99, 50, 200, 5),
            ("Energy Drink 250ml", "8901234567894", 0, 0, 249, 150, 90, 18),

            # Dairy
            ("Fresh Milk 1L", "8901234567895", 1, 0, 299, 200, 60, 12),
            ("Greek Yogurt 500g", "8901234567896", 1, 0, 449, 300, 45, 12),
            ("Cheddar Cheese 200g", "8901234567897", 1, 0, 599, 400, 30, 12),
            ("Butter 250g", "8901234567898", 1, 0, 399, 250, 40, 12),

            # Bakery
            ("White Bread", "8901234567899", 2, 0, 249, 150, 70, 0),
            ("Whole Wheat Bread", "8901234567900", 2, 0, 299, 180, 55, 0),
            ("Croissant Pack (6)", "8901234567901", 2, 0, 499, 300, 25, 12),
            ("Bagels Pack (6)", "8901234567902", 2, 0, 399, 250, 30, 12),

            # Snacks
            ("Potato Chips 150g", "8901234567903", 3, 0, 299, 180, 100, 12),
            ("Chocolate Bar", "8901234567904", 3, 0, 149, 80, 200, 18),
            ("Cookies Pack", "8901234567905", 3, 0, 349, 200, 85, 12),
            ("Nuts Mix 250g", "8901234567906", 3, 0, 599, 350, 45, 12),

            # Household
            ("Dish Soap 500ml", "8901234567907", 4, 0, 299, 180, 60, 18),
            ("Laundry Detergent 1L", "8901234567908", 4, 0, 699, 450, 40, 18),
            ("Paper Towels (4 rolls)", "8901234567909", 4, 0, 499, 300, 50, 12),
            ("Toilet Paper (12 rolls)", "8901234567910", 4, 0, 899, 600, 35, 12),

            # Personal Care
            ("Shampoo 400ml", "8901234567911", 5, 0, 599, 350, 45, 18),
            ("Toothpaste 100ml", "8901234567912", 5, 0, 299, 180, 80, 18),
            ("Soap Bar (3 pack)", "8901234567913", 5, 0, 399, 230, 60, 18),

            # Fresh Produce
            ("Bananas (per kg)", "8901234567914", 6, 0, 199, 120, 100, 0),
            ("Apples (per kg)", "8901234567915", 6, 0, 299, 200, 80, 0),
            ("Tomatoes (per kg)", "8901234567916", 6, 0, 249, 150, 70, 0),
            ("Potatoes (per kg)", "8901234567917", 6, 0, 149, 90, 120, 0),
            ("Onions (per kg)", "8901234567918", 6, 0, 129, 80, 90, 0),

            # Frozen Foods
            ("Frozen Pizza", "8901234567919", 7, 0, 599, 380, 40, 12),
            ("Ice Cream 1L", "8901234567920", 7, 0, 499, 300, 35, 12),
            ("Frozen Vegetables 1kg", "8901234567921", 7, 0, 399, 250, 50, 12),

            # More Snacks
            ("Popcorn 100g", "8901234567922", 3, 0, 199, 110, 60, 12),
            ("Granola Bars (6)", "8901234567923", 3, 0, 349, 200, 75, 12),
            ("Dried Fruits 200g", "8901234567924", 3, 0, 499, 300, 40, 12),

            # More Beverages
            ("Iced Tea 1L", "8901234567925", 0, 0, 399, 240, 50, 12),
            ("Coffee Beans 250g", "8901234567926", 0, 0, 799, 500, 30, 18),
            ("Green Tea Box (20)", "8901234567927", 0, 0, 249, 150, 70, 12),

            # More Dairy
            ("Paneer 200g", "8901234567928", 1, 1, 399, 280, 35, 12),
            ("Cream 200ml", "8901234567929", 1, 1, 299, 200, 45, 12),
            ("Lassi 250ml", "8901234567930", 1, 0, 99, 60, 100, 12),

            # More Household
            ("Air Freshener 300ml", "8901234567931", 4, 0, 349, 200, 40, 18),
            ("Bin Bags (50 pcs)", "8901234567932", 4, 0, 499, 300, 55, 12),
            ("Sponges (6 pack)", "8901234567933", 4, 0, 199, 120, 80, 12),

            # More Personal Care
            ("Face Cream 50g", "8901234567934", 5, 0, 499, 300, 35, 18),
            ("Razor Pack (5)", "8901234567935", 5, 0, 299, 170, 60, 18),
            ("Moisturizer 200ml", "8901234567936", 5, 0, 449, 270, 40, 18),
        ]

        products = []
        for i, (name, barcode, cat_idx, sup_idx, mrp, purchase, stock, gst) in enumerate(products_data):
            product = Product(
                barcode=barcode,
                name=name,
                category_id=cat_idx + 1,  # IDs are 1-indexed
                supplier_id=sup_idx + 1 if sup_idx > 0 else None,
                mrp_paise=mrp,
                purchase_price_paise=purchase,
                selling_price_paise=mrp,  # Same as MRP initially
                gst_rate=gst,
                stock_quantity=stock,
                reorder_level=10,
                default_discount_percent=0,
                is_active=True
            )
            session.add(product)
            products.append(product)

        await session.flush()
        print(f"✓ Created {len(products_data)} products")

        # Create stock batches (with some expiring soon for testing)
        for i, product in enumerate(products):
            batch = StockBatch(
                product_id=product.id,
                batch_number=f"BATCH-{product.id:04d}-001",
                quantity=product.stock_quantity,
                initial_quantity=product.stock_quantity,
                purchase_price_paise=product.purchase_price_paise,
                expiry_date=datetime.utcnow() + timedelta(days=365 if i % 3 != 0 else 5),  # Some expiring soon
                is_active=True
            )
            session.add(batch)

        await session.flush()
        print(f"✓ Created {len(products)} stock batches")

        # Create sample customers
        customers = [
            Customer(
                name="John Smith",
                phone="555-0101",
                email="john.smith@email.com",
                address="123 Main St",
                loyalty_points=150
            ),
            Customer(
                name="Sarah Johnson",
                phone="555-0102",
                email="sarah.j@email.com",
                address="456 Oak Ave",
                loyalty_points=280
            ),
            Customer(
                name="Michael Brown",
                phone="555-0103",
                email="mbrown@email.com",
                address="789 Pine Rd",
                loyalty_points=420
            ),
        ]
        for cust in customers:
            session.add(cust)

        await session.flush()
        print(f"✓ Created {len(customers)} customers")

        await session.commit()
        print("\n" + "="*50)
        print("✓ Seed data created successfully!")
        print("="*50)
        print("\nLogin Credentials:")
        print("-" * 50)
        print("Admin:       admin / admin123")
        print("Manager:     manager1 / manager123")
        print("Cashier:     cashier1 / cashier123")
        print("Inventory:   inventory1 / inventory123")
        print("-" * 50)


if __name__ == "__main__":
    import sqlalchemy as sa
    # Import models for Base
    from app.models import User, Category, Supplier, Product, StockBatch, Customer, Purchase, PurchaseItem, Invoice, InvoiceItem, StockMovement, AuditLog
    asyncio.run(create_seed_data())