"""
Setup script to populate the database with sample data
"""
from app import app, db, User, Product, Customer, Transaction, TransactionItem
from datetime import datetime, timedelta
import random

def setup_sample_data():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Creating users...")
        # Create admin user
        admin = User(
            username='admin',
            full_name='System Administrator',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create manager
        manager = User(
            username='manager1',
            full_name='Store Manager',
            role='manager'
        )
        manager.set_password('manager123')
        db.session.add(manager)

        # Create cashiers
        cashier1 = User(
            username='cashier1',
            full_name='John Cashier',
            role='cashier'
        )
        cashier1.set_password('cashier123')
        db.session.add(cashier1)

        cashier2 = User(
            username='cashier2',
            full_name='Jane Cashier',
            role='cashier'
        )
        cashier2.set_password('cashier123')
        db.session.add(cashier2)

        db.session.commit()
        print("✓ Users created")

        print("Creating products...")
        # Sample products
        products_data = [
            # Beverages
            ('Coca Cola 500ml', '8901234567890', 'Beverages', 1.99, 1.20, 150, 20),
            ('Pepsi 500ml', '8901234567891', 'Beverages', 1.99, 1.20, 120, 20),
            ('Orange Juice 1L', '8901234567892', 'Beverages', 3.49, 2.10, 80, 15),
            ('Mineral Water 1L', '8901234567893', 'Beverages', 0.99, 0.50, 200, 30),
            ('Energy Drink 250ml', '8901234567894', 'Beverages', 2.49, 1.50, 90, 15),

            # Dairy
            ('Fresh Milk 1L', '8901234567895', 'Dairy', 2.99, 2.00, 60, 20),
            ('Greek Yogurt 500g', '8901234567896', 'Dairy', 4.49, 3.00, 45, 15),
            ('Cheddar Cheese 200g', '8901234567897', 'Dairy', 5.99, 4.00, 30, 10),
            ('Butter 250g', '8901234567898', 'Dairy', 3.99, 2.50, 40, 15),

            # Bakery
            ('White Bread', '8901234567899', 'Bakery', 2.49, 1.50, 70, 20),
            ('Whole Wheat Bread', '8901234567900', 'Bakery', 2.99, 1.80, 55, 20),
            ('Croissant Pack (6)', '8901234567901', 'Bakery', 4.99, 3.00, 25, 10),
            ('Bagels Pack (6)', '8901234567902', 'Bakery', 3.99, 2.50, 30, 10),

            # Snacks
            ('Potato Chips 150g', '8901234567903', 'Snacks', 2.99, 1.80, 100, 25),
            ('Chocolate Bar', '8901234567904', 'Snacks', 1.49, 0.80, 200, 40),
            ('Cookies Pack', '8901234567905', 'Snacks', 3.49, 2.00, 85, 20),
            ('Nuts Mix 250g', '8901234567906', 'Snacks', 5.99, 3.50, 45, 15),

            # Household
            ('Dish Soap 500ml', '8901234567907', 'Household', 2.99, 1.80, 60, 15),
            ('Laundry Detergent 1L', '8901234567908', 'Household', 6.99, 4.50, 40, 10),
            ('Paper Towels (4 rolls)', '8901234567909', 'Household', 4.99, 3.00, 50, 15),
            ('Toilet Paper (12 rolls)', '8901234567910', 'Household', 8.99, 6.00, 35, 10),

            # Fresh Produce
            ('Bananas (per kg)', '8901234567911', 'Fresh Produce', 1.99, 1.20, 100, 30),
            ('Apples (per kg)', '8901234567912', 'Fresh Produce', 2.99, 2.00, 80, 25),
            ('Tomatoes (per kg)', '8901234567913', 'Fresh Produce', 2.49, 1.50, 70, 20),
            ('Potatoes (per kg)', '8901234567914', 'Fresh Produce', 1.49, 0.90, 120, 30),
            ('Onions (per kg)', '8901234567915', 'Fresh Produce', 1.29, 0.80, 90, 25),

            # Frozen Foods
            ('Frozen Pizza', '8901234567916', 'Frozen Foods', 5.99, 3.80, 40, 15),
            ('Ice Cream 1L', '8901234567917', 'Frozen Foods', 4.99, 3.00, 35, 10),
            ('Frozen Vegetables 1kg', '8901234567918', 'Frozen Foods', 3.99, 2.50, 50, 15),

            # Personal Care
            ('Shampoo 400ml', '8901234567919', 'Personal Care', 5.99, 3.50, 45, 15),
            ('Toothpaste 100ml', '8901234567920', 'Personal Care', 2.99, 1.80, 80, 20),
            ('Soap Bar (3 pack)', '8901234567921', 'Personal Care', 3.99, 2.30, 60, 15),
        ]

        for name, barcode, category, unit_price, cost_price, stock, min_stock in products_data:
            product = Product(
                name=name,
                barcode=barcode,
                category=category,
                unit_price=unit_price,
                cost_price=cost_price,
                stock_quantity=stock,
                min_stock_level=min_stock,
                description=f'{category} item'
            )
            db.session.add(product)

        db.session.commit()
        print(f"✓ {len(products_data)} products created")

        print("Creating customers...")
        # Sample customers
        customers_data = [
            ('John Smith', '555-0101', 'john.smith@email.com', '123 Main St', 150),
            ('Sarah Johnson', '555-0102', 'sarah.j@email.com', '456 Oak Ave', 280),
            ('Michael Brown', '555-0103', 'mbrown@email.com', '789 Pine Rd', 420),
            ('Emily Davis', '555-0104', 'emily.d@email.com', '321 Elm St', 95),
            ('David Wilson', '555-0105', 'dwilson@email.com', '654 Maple Dr', 310),
        ]

        for name, phone, email, address, points in customers_data:
            customer = Customer(
                name=name,
                phone=phone,
                email=email,
                address=address,
                loyalty_points=points
            )
            db.session.add(customer)

        db.session.commit()
        print(f"✓ {len(customers_data)} customers created")

        print("Creating sample transactions...")
        # Create transactions for the last 30 days
        products = Product.query.all()
        customers = Customer.query.all()
        users = User.query.filter(User.role.in_(['cashier', 'manager'])).all()

        transactions_created = 0
        for day_offset in range(30):
            transaction_date = datetime.utcnow() - timedelta(days=day_offset)

            # Random number of transactions per day (5-15)
            num_transactions = random.randint(5, 15)

            for _ in range(num_transactions):
                # Random customer (or walk-in)
                customer = random.choice(customers) if random.random() > 0.3 else None
                user = random.choice(users)

                # Random transaction time
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                transaction_time = transaction_date.replace(hour=hour, minute=minute)

                # Random number of items (1-6)
                num_items = random.randint(1, 6)
                selected_products = random.sample(products, num_items)

                subtotal = 0
                transaction_items = []

                for product in selected_products:
                    quantity = random.randint(1, 3)
                    item_total = product.unit_price * quantity
                    subtotal += item_total

                    transaction_items.append({
                        'product': product,
                        'quantity': quantity,
                        'unit_price': product.unit_price,
                        'total_price': item_total
                    })

                # Calculate tax and total
                tax_amount = subtotal * 0.10  # 10% tax
                discount_amount = 0
                if customer and random.random() > 0.7:  # 30% chance of discount for members
                    discount_amount = subtotal * 0.05  # 5% discount

                total_amount = subtotal + tax_amount - discount_amount

                # Create transaction
                transaction = Transaction(
                    transaction_number=f"TRX-{transaction_time.strftime('%Y%m%d')}-{transactions_created + 1:04d}",
                    customer_id=customer.id if customer else None,
                    user_id=user.id,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                    payment_method=random.choice(['cash', 'card', 'mobile']),
                    payment_status='completed',
                    created_at=transaction_time
                )
                db.session.add(transaction)
                db.session.flush()

                # Add transaction items
                for item_data in transaction_items:
                    item = TransactionItem(
                        transaction_id=transaction.id,
                        product_id=item_data['product'].id,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price'],
                        total_price=item_data['total_price']
                    )
                    db.session.add(item)

                transactions_created += 1

        db.session.commit()
        print(f"✓ {transactions_created} transactions created")

        print("\n" + "="*50)
        print("✓ Database setup completed successfully!")
        print("="*50)
        print("\nLogin Credentials:")
        print("-" * 50)
        print("Admin:    username: admin     password: admin123")
        print("Manager:  username: manager1  password: manager123")
        print("Cashier:  username: cashier1  password: cashier123")
        print("Cashier:  username: cashier2  password: cashier123")
        print("-" * 50)
        print("\nYou can now run the application with: python app.py")
        print("Then visit: http://localhost:5000")
        print("="*50)

if __name__ == '__main__':
    setup_sample_data()