# Supermarket Billing System

A production-ready supermarket billing system with inventory management, POS, and analytics dashboard.

## Features

- **User Authentication** - Secure login with role-based access (Admin, Manager, Cashier)
- **Dashboard** - Real-time stats, charts, and recent transactions
- **Inventory Management** - Product tracking with low-stock alerts
- **Point of Sale** - Quick billing with barcode support
- **Transaction History** - Complete sales records with search/filter
- **Analytics** - Daily revenue trends, category sales charts

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database with Sample Data

```bash
python setup_data.py
```

This creates:
- 3 users (admin, manager, cashier)
- 30 sample products across categories
- 5 sample customers
- 30 days of transaction history

### 3. Run the Application

```bash
python app.py
```

Then open http://localhost:5000 in your browser.

## Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Manager | manager1 | manager123 |
| Cashier | cashier1 | cashier123 |

## Project Structure

```
supermarket_billing_system/
├── app.py              # Main Flask application
├── setup_data.py       # Database initialization script
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── templates/
    ├── login.html     # Login page
    └── dashboard.html # Main dashboard
```

## API Endpoints

- `POST /login` - User authentication
- `GET /api/stats` - Dashboard statistics
- `GET/POST /api/products` - Product management
- `GET/POST /api/transactions` - Transaction management
- `GET /api/customers` - Customer management
- `GET /api/charts/daily-revenue` - Revenue chart data
- `GET /api/charts/category-sales` - Category sales chart

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Plotly.js
- **Authentication**: Session-based with password hashing