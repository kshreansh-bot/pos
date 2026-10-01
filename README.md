# Supermarket POS & Inventory System

A production-ready Supermarket Point of Sale (POS) and Inventory Management System built with FastAPI, SQLAlchemy 2.x, React, and TypeScript.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access control (Admin, Manager, Cashier, Inventory Manager)
- **Money Handling**: All amounts stored as integer paise (no floating-point errors)
- **GST Support**: GST-inclusive pricing with tax extraction and grouping
- **Stock Management**: Batch tracking with FEFO (First Expiry, First Out)
- **POS**: Keyboard-first interface with barcode scanning
- **Invoicing**: Sequential invoice numbers with QR codes for public access
- **Audit Trail**: Complete history of price changes, stock movements, and transactions

## Tech Stack

### Backend
- **FastAPI**: Modern async web framework
- **SQLAlchemy 2.x**: ORM with async support
- **Alembic**: Database migrations
- **Pydantic v2**: Data validation
- **SQLite**: Database (WAL mode enabled)
- **JWT + bcrypt**: Authentication

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **React Router**: Navigation

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file**
   ```bash
   copy .env.example .env
   # Edit .env and set SECRET_KEY to a secure random string (min 32 chars)
   ```

5. **Initialize database**
   ```bash
   # Create database schema
   python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
   ```

6. **Seed demo data**
   ```bash
   python scripts/seed_data.py
   ```

7. **Run the server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   The API will be available at: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs
   - Health Check: http://localhost:8000/health

### Frontend Setup (Coming in Phase 4)

```bash
cd frontend
npm install
npm run dev
```

## Login Credentials

After running the seed script, use these credentials:

| Role       | Username   | Password     | Permissions |
|------------|------------|--------------|-------------|
| Admin      | admin      | admin123     | Full access |
| Manager    | manager1   | manager123   | Products, inventory, reports |
| Cashier    | cashier1   | cashier123   | POS, sales |
| Inventory  | inventory1 | inventory123 | Stock management |

## API Endpoints

### Authentication
- `POST /auth/login` - Login with username/password
- `POST /auth/logout` - Logout (client-side token deletion)
- `GET /auth/me` - Get current user info

### Users (Admin only)
- `GET /users` - List all users
- `GET /users/{id}` - Get user by ID
- `POST /users` - Create new user
- `PUT /users/{id}` - Update user

### Health
- `GET /health` - Health check

## Testing

Run the test suite:

```bash
cd backend
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

## Project Structure

```
supermarket_billing_system/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── services/         # Business logic
│   │   ├── utils/            # Utilities (money, errors)
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── database.py       # Database session
│   │   ├── config.py         # Settings
│   │   └── main.py           # FastAPI app
│   ├── migrations/           # Alembic migrations
│   ├── tests/                # Test suite
│   ├── scripts/              # Utility scripts
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment template
├── frontend/                 # React frontend (Phase 4)
├── CLAUDE.md                 # Development guide
└── README.md                 # This file
```

## Development Phase Status

- ✅ **Phase 1: Foundation** - Project setup, auth, DB models
- ⏳ **Phase 2: Products & Inventory** - Products, suppliers, batches
- ⏳ **Phase 3: Billing Engine** - Invoice creation, QR codes
- ⏳ **Phase 4: POS UI** - React frontend
- ⏳ **Phase 5: Returns & Audit** - Returns, voids, audit log
- ⏳ **Phase 6: Reports** - Analytics and reporting

## Core Business Rules

1. **Money**: All amounts stored as integer paise (1 rupee = 100 paise)
2. **GST**: Selling prices are GST-inclusive; tax extracted per line
3. **Stock**: FEFO (First Expiry, First Out) with batch tracking
4. **Transactions**: Atomic operations with full rollback on failure
5. **Invoices**: Sequential numbering with immutable snapshots
6. **Audit**: Complete trail of all critical operations

## License

Proprietary - All rights reserved

## Support

For issues or questions, please refer to CLAUDE.md for detailed documentation.
