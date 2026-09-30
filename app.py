#!/usr/bin/env python3
"""
Supermarket Billing System - Main Application
A production-ready billing system with inventory management, POS, and analytics.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import plotly
import plotly.graph_objs as go
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///supermarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # admin, manager, cashier
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(50), unique=True)
    category = db.Column(db.String(100), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    min_stock_level = db.Column(db.Integer, nullable=False, default=10)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'barcode': self.barcode,
            'category': self.category,
            'unit_price': self.unit_price,
            'cost_price': self.cost_price,
            'stock_quantity': self.stock_quantity,
            'min_stock_level': self.min_stock_level,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # cash, card, mobile
    payment_status = db.Column(db.String(20), nullable=False, default='completed')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer', backref='transactions')
    user = db.relationship('User', backref='transactions')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_number': self.transaction_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else 'Walk-in Customer',
            'user_id': self.user_id,
            'user_name': self.user.full_name,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    transaction = db.relationship('Transaction', backref='items')
    product = db.relationship('Product', backref='transaction_items')

# Authentication decorator
def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role:
                user = User.query.get(session['user_id'])
                if not user or user.role not in role:
                    return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['user_role'] = user.role
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'name': user.full_name,
                    'role': user.role
                }
            })
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
@login_required()
def get_stats():
    # Today's stats
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Today's transactions
    today_transactions = Transaction.query.filter(
        Transaction.created_at >= today_start,
        Transaction.created_at <= today_end
    ).all()

    # Total transactions count
    total_transactions = Transaction.query.count()

    # Today's revenue
    today_revenue = sum(t.total_amount for t in today_transactions)

    # Total revenue
    total_revenue_result = db.session.query(db.func.sum(Transaction.total_amount)).scalar()
    total_revenue = total_revenue_result or 0

    # Low stock items
    low_stock_items = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level
    ).count()

    # Recent transactions
    recent_transactions = Transaction.query.order_by(
        Transaction.created_at.desc()
    ).limit(5).all()

    # Top selling products (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    top_products = db.session.query(
        Product.name,
        db.func.sum(TransactionItem.quantity).label('total_quantity')
    ).join(TransactionItem, TransactionItem.product_id == Product.id)\
     .join(Transaction, Transaction.id == TransactionItem.transaction_id)\
     .filter(Transaction.created_at >= seven_days_ago)\
     .group_by(Product.id)\
     .order_by(db.desc('total_quantity'))\
     .limit(5).all()

    return jsonify({
        'today': {
            'revenue': round(today_revenue, 2),
            'transactions': len(today_transactions),
            'average_ticket': round(today_revenue / len(today_transactions), 2) if today_transactions else 0
        },
        'overall': {
            'revenue': round(total_revenue, 2),
            'transactions': total_transactions,
            'low_stock_items': low_stock_items
        },
        'recent_transactions': [t.to_dict() for t in recent_transactions],
        'top_products': [
            {'name': p[0], 'quantity': int(p[1])} for p in top_products
        ]
    })

@app.route('/api/transactions', methods=['GET', 'POST'])
@login_required(role=['admin', 'manager', 'cashier'])
def transactions():
    if request.method == 'POST':
        data = request.json
        transaction_number = f"TRX-{datetime.utcnow().strftime('%Y%m%d')}-{Transaction.query.count() + 1:04d}"

        # Create transaction
        transaction = Transaction(
            transaction_number=transaction_number,
            customer_id=data.get('customer_id'),
            user_id=session['user_id'],
            subtotal=data['subtotal'],
            tax_amount=data['tax_amount'],
            discount_amount=data.get('discount_amount', 0),
            total_amount=data['total_amount'],
            payment_method=data['payment_method'],
            payment_status='completed',
            notes=data.get('notes', '')
        )
        db.session.add(transaction)
        db.session.flush()  # Get transaction ID

        # Add transaction items
        for item in data['items']:
            product = Product.query.get(item['product_id'])
            if product:
                transaction_item = TransactionItem(
                    transaction_id=transaction.id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    total_price=item['total_price']
                )
                db.session.add(transaction_item)

                # Update stock
                product.stock_quantity -= item['quantity']

        db.session.commit()

        return jsonify({
            'success': True,
            'transaction_id': transaction.id,
            'transaction_number': transaction_number
        })

    # GET method - list transactions
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Transaction.query

    if start_date:
        query = query.filter(Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(Transaction.created_at <= end_date)

    transactions = query.order_by(Transaction.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': transactions.page
    })

@app.route('/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required(role=['admin', 'manager'])
def products():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        category = request.args.get('category')
        search = request.args.get('search')

        query = Product.query

        if category:
            query = query.filter(Product.category == category)
        if search:
            query = query.filter(Product.name.ilike(f'%{search}%'))

        products = query.order_by(Product.name)\
                        .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'products': [p.to_dict() for p in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': products.page
        })

    elif request.method == 'POST':
        data = request.json
        product = Product(
            name=data['name'],
            barcode=data.get('barcode'),
            category=data['category'],
            unit_price=data['unit_price'],
            cost_price=data['cost_price'],
            stock_quantity=data.get('stock_quantity', 0),
            min_stock_level=data.get('min_stock_level', 10),
            description=data.get('description', '')
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True, 'product': product.to_dict()}), 201

    elif request.method == 'PUT':
        data = request.json
        product = Product.query.get(data['id'])
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        product.name = data['name']
        product.barcode = data.get('barcode')
        product.category = data['category']
        product.unit_price = data['unit_price']
        product.cost_price = data['cost_price']
        product.stock_quantity = data['stock_quantity']
        product.min_stock_level = data['min_stock_level']
        product.description = data.get('description', '')

        db.session.commit()
        return jsonify({'success': True, 'product': product.to_dict()})

    elif request.method == 'DELETE':
        product_id = request.args.get('id')
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        # Check if product is in any transactions
        if product.transaction_items:
            return jsonify({'error': 'Cannot delete product with existing transactions'}), 400

        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/customers', methods=['GET', 'POST', 'PUT'])
@login_required(role=['admin', 'manager'])
def customers():
    if request.method == 'GET':
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = Customer.query

        if search:
            query = query.filter(
                db.or_(
                    Customer.name.ilike(f'%{search}%'),
                    Customer.phone.ilike(f'%{search}%'),
                    Customer.email.ilike(f'%{search}%')
                )
            )

        customers = query.order_by(Customer.created_at.desc())\
                         .paginate(page=page, per_page=per_page, error_out=False)

        customers_data = [{
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'email': c.email,
            'address': c.address,
            'loyalty_points': c.loyalty_points,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in customers.items]

        return jsonify({
            'customers': customers_data,
            'total': customers.total,
            'pages': customers.pages,
            'current_page': customers.page
        })

    elif request.method == 'POST':
        data = request.json
        customer = Customer(
            name=data['name'],
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            loyalty_points=data.get('loyalty_points', 0)
        )
        db.session.add(customer)
        db.session.commit()
        return jsonify({'success': True, 'customer_id': customer.id}), 201

    elif request.method == 'PUT':
        data = request.json
        customer = Customer.query.get(data['id'])
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        customer.name = data['name']
        customer.phone = data.get('phone')
        customer.email = data.get('email')
        customer.address = data.get('address')
        customer.loyalty_points = data.get('loyalty_points', 0)

        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/charts/daily-revenue')
@login_required(role=['admin', 'manager'])
def daily_revenue_chart():
    # Get revenue for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_revenue = db.session.query(
        db.func.date(Transaction.created_at).label('date'),
        db.func.sum(Transaction.total_amount).label('revenue')
    ).filter(Transaction.created_at >= thirty_days_ago)\
     .group_by(db.func.date(Transaction.created_at))\
     .order_by('date')\
     .all()

    dates = [r[0].strftime('%Y-%m-%d') for r in daily_revenue]
    revenues = [float(r[1]) for r in daily_revenue]

    # Create Plotly chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=revenues,
        mode='lines+markers',
        name='Daily Revenue',
        line=dict(color='#3B82F6', width=3),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title='Daily Revenue (Last 30 Days)',
        xaxis_title='Date',
        yaxis_title='Revenue ($)',
        template='plotly_white',
        height=400,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return jsonify({
        'chart': json.loads(plotly.io.to_json(fig)),
        'data': {
            'dates': dates,
            'revenues': revenues
        }
    })

@app.route('/api/charts/category-sales')
@login_required(role=['admin', 'manager'])
def category_sales_chart():
    # Get sales by category for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    category_sales = db.session.query(
        Product.category,
        db.func.sum(TransactionItem.total_price).label('sales')
    ).join(TransactionItem, TransactionItem.product_id == Product.id)\
     .join(Transaction, Transaction.id == TransactionItem.transaction_id)\
     .filter(Transaction.created_at >= thirty_days_ago)\
     .group_by(Product.category)\
     .order_by(db.desc('sales'))\
     .limit(10).all()

    categories = [r[0] for r in category_sales]
    sales = [float(r[1]) for r in category_sales]

    # Create Plotly pie chart
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=sales,
        hole=.3,
        marker=dict(colors=[
            '#3B82F6', '#10B981', '#EF4444', '#F59E0B', '#8B5CF6',
            '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16'
        ])
    )])

    fig.update_layout(
        title='Sales by Category (Last 30 Days)',
        template='plotly_white',
        height=400,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return jsonify({
        'chart': json.loads(plotly.io.to_json(fig)),
        'data': {
            'categories': categories,
            'sales': sales
        }
    })

@app.route('/api/pos/search-products')
@login_required(role=['admin', 'manager', 'cashier'])
def search_products():
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)

    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        )
    ).filter(Product.stock_quantity > 0)\
     .order_by(Product.name)\
     .limit(limit).all()

    return jsonify([{
        'id': p.id,
        'name': p.name,
        'barcode': p.barcode,
        'category': p.category,
        'unit_price': p.unit_price,
        'stock_quantity': p.stock_quantity,
        'description': p.description
    } for p in products])

@app.route('/api/inventory/low-stock')
@login_required(role=['admin', 'manager'])
def low_stock_items():
    items = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level
    ).order_by(Product.stock_quantity).all()

    return jsonify([{
        'id': p.id,
        'name': p.name,
        'current_stock': p.stock_quantity,
        'min_stock': p.min_stock_level,
        'category': p.category,
        'unit_price': p.unit_price,
        'needed': p.min_stock_level - p.stock_quantity
    } for p in items])

# Initialize database and create admin user
def init_db():
    with app.app_context():
        db.create_all()

        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                full_name='System Administrator',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # Add sample cashier
            cashier = User(
                username='cashier1',
                full_name='John Cashier',
                role='cashier'
            )
            cashier.set_password('cashier123')
            db.session.add(cashier)

            db.session.commit()
            print("Database initialized with admin user (username: admin, password: admin123)")
            print("Sample cashier (username: cashier1, password: cashier123)")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)