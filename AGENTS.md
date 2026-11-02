# Supermarket POS & Inventory System - AGENTS.md

**Status**: Phase 1 - Foundation (in progress)

## Architecture

### Backend Stack
- **Framework**: FastAPI (async, modern, built-in validation)
- **Database**: SQLite (WAL mode, foreign keys ON)
- **ORM**: SQLAlchemy 2.x with async support
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Auth**: JWT (access tokens, bcrypt password hashing)
- **Task Structure**: Routers → Services (business logic) → Repositories/Models

### Frontend Stack
- **Framework**: React + TypeScript + Vite
- **Styling**: Plain CSS (structured, semantic)
- **Router**: React Router for navigation
- **State**: React hooks (no external state management)
- **UI Patterns**: Keyboard-first POS, barcode input focus

### Database Design
- **Money**: All amounts stored as integer paise (multiply by 100, never floats)
- **Rounding**: Per-line, round-half-up (banker's rounding disabled)
- **Prices**: Selling price is GST-inclusive; tax extracted per line per rate
- **Stock**: Tracked per batch (batch_no, expiry_date, quantity)
- **FEFO**: Sell nearest-expiry first; block expired batches
- **Transactions**: Atomic (validate → create invoice/items → deduct stock → record movements)
- **Invoice Snapshot**: Product data (name, price, tax rate) copied to invoice lines
- **QR Token**: Random 128-bit value (not sequential), public bill page read-only

## Core Business Rules

1. **Money Handling**
   - Store all amounts as integers (paise, not rupees)
   - Single shared `round_half_up(value, decimals)` function
   - Never use float arithmetic; convert to paise first
   - Tax calculation: `(price * rate) / 100`, then round per line

2. **GST & Taxation**
   - Selling price in system is GST-inclusive
   - Extract tax per line: `tax = price - (price / (1 + rate/100))`
   - Group by rate on invoice (0%, 5%, 12%, 18%, 28%)
   - Invoice shows: net amount, tax, total per rate

3. **Stock Management**
   - Track per batch: batch_no, expiry_date, quantity
   - FEFO: sort by expiry, sell nearest-expiry first
   - Block sales of expired items
   - Warn at configurable days_to_expiry (e.g., 7 days)
   - Stock movement ledger: receipt, sale, adjustment (reason logged)

4. **Sale Completion**
   - Single database transaction:
     1. Validate: stock available, not expired, cashier discount limit
     2. Create invoice with snapshot data
     3. Create invoice_items (snapshot: product name/price/tax_rate)
     4. Deduct stock per batch (FEFO order)
     5. Record stock movements
   - Fail → full rollback
   - Prevent overselling under concurrency (transaction-level check)

5. **Invoices & QR**
   - Sequential format: INV-2026-000001 (per year)
   - QR encodes `/bill/{public_token}` (128-bit random, not invoice ID)
   - Public bill page: no login, read-only, mobile-friendly, rate-limited
   - Never retroactively modify past bills (snapshot prevents this)

6. **Returns & Voids**
   - Never delete data; use status (completed/cancelled/returned)
   - Reversing movements: reverse stock deduction, record reason in audit log
   - Audit log: who/what/when for price changes, stock adjustments, discounts, voids

## API Design

### Authentication Flow
- `POST /auth/register` (admin only) → JWT token
- `POST /auth/login` → access token (JWT) + token expiry
- `POST /auth/refresh` → new access token
- All endpoints: require valid JWT in `Authorization: Bearer <token>`
- Role-based: @require_role(['admin', 'cashier']) guards on routers

### Core Endpoints (Phase 1)
- `POST /auth/login` - User authentication
- `GET /users`, `POST /users`, `PUT /users/{id}` - User management (admin)
- `POST /auth/logout` - Invalidate session

### Later Phases
- Products, inventory, batches, suppliers
- POS cart, checkout, invoices, QR
- Customers, returns, reports

## Project Structure

```
supermarket_billing_system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings (env vars)
│   │   ├── dependencies.py         # Auth, DB session injection
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Login, register
│   │   │   ├── users.py            # User CRUD
│   │   │   └── ... (products, pos, etc.)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py     # JWT, password hashing, business logic
│   │   │   ├── user_service.py
│   │   │   └── ... (product, pos, etc.)
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── base.py             # Generic CRUD
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── money.py            # round_half_up, paise conversions
│   │       └── errors.py           # Custom exceptions
│   ├── migrations/                 # Alembic
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_money.py           # Rounding, tax math
│   │   └── ... (business logic)
│   ├── requirements.txt
│   ├── .env.example
│   └── alembic.ini
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── ... (React components)
    │   ├── pages/
    │   │   └── ... (route pages)
    │   ├── services/
    │   │   └── api.ts              # Fetch wrapper, auth headers
    │   ├── types/
    │   │   └── index.ts            # TypeScript interfaces
    │   ├── App.tsx
    │   └── main.tsx
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json
```

## Commands

### Backend Setup
```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Seed sample data
python scripts/seed_data.py

# Run server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest --cov=app tests/

# Create migration
alembic revision --autogenerate -m "description"
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev          # Dev server on :5173
npm run build        # Production build
npm run test         # Vitest
```

## Development Conventions

### Python
- **Type hints**: everywhere (FastAPI docs, IDE support, type checking)
- **Docstrings**: module, class, function level; describe intent, not obvious code
- **Error handling**: Custom exceptions in `utils/errors.py`; catch and convert to HTTP responses
- **Logging**: Structured logging (request ID, user, action)
- **Testing**: Unit tests in `tests/`; mock services, DB with SQLite in-memory
- **Code style**: Black (line length 88), isort, flake8

### TypeScript
- **Strict mode**: enabled in tsconfig.json
- **Type safety**: no `any` types; use interfaces/types
- **API calls**: Centralized in `services/api.ts` with error handling
- **Components**: Functional, hooks-based; props as interfaces
- **State**: React hooks (useState, useContext); no Redux/Zustand

### Database
- **Migrations**: One migration per feature; reversible
- **Foreign keys**: ON (enforced)
- **Indexes**: On frequently queried columns (barcode, phone, batch_id)
- **WAL mode**: Enabled for concurrent reads

## Testing Strategy

### Backend (pytest + httpx)
- **Unit**: Money math (rounding edge cases), tax extraction, FEFO selection
- **Integration**: Auth flow, role checks, transaction rollback
- **API**: GET/POST/PUT/DELETE per role; 403 for unauthorized
- **Fixtures**: In-memory SQLite, test users, sample products/batches

### Frontend (Vitest + React Testing Library)
- **Cart logic**: Add item, update qty, remove, discount application
- **Money display**: Paise to rupees, formatting
- **POS keyboard**: Barcode focus, Enter adds item

### End-to-End (manual or Playwright later)
- Fresh clone → install → migrate → seed → run
- Cashier flow: scan barcode, complete sale, see QR

## Phase Checklist (Phase 1: Foundation)

- [ ] Project structure: backend (FastAPI + SQLAlchemy), frontend (React + Vite)
- [ ] Git setup: `.gitignore`, initial commit
- [ ] Backend:
  - [ ] Dependencies: FastAPI, SQLAlchemy, Alembic, Pydantic, bcrypt, python-jose, python-dotenv
  - [ ] Config: Settings from `.env`
  - [ ] Models: User, Role (enum)
  - [ ] Schemas: UserCreate, UserResponse, LoginRequest
  - [ ] Auth: JWT creation/verification, password hashing, login endpoint
  - [ ] Migrations: Initial schema
  - [ ] Tests: Auth (login, JWT validation, role checks)
- [ ] Frontend:
  - [ ] Vite project with TypeScript
  - [ ] React Router setup (/, /login, /dashboard)
  - [ ] Login form, auth context, API client
  - [ ] .env.example with VITE_API_URL
  - [ ] Tailwind (or plain CSS) base styling
- [ ] Database:
  - [ ] SQLite initialized (WAL mode, foreign keys ON)
  - [ ] Migrations version table created
- [ ] Seed script: 3 users (admin, cashier, manager), demo data
- [ ] README: Fresh clone → install → migrate → seed → run, login credentials
- [ ] Run & verify:
  - [ ] Backend starts, health check responds
  - [ ] Frontend dev server starts, login page loads
  - [ ] Login with test user, JWT received
  - [ ] Role check: cashier cannot access admin endpoints
  - [ ] All tests pass

## Definition of Done (Phase 1)
- Fresh clone: `pip install` → `alembic upgrade head` → `python scripts/seed_data.py` → `uvicorn app.main:app --reload` works
- Frontend: `npm install` → `npm run dev` works, login form loads
- Auth flow: POST /auth/login with credentials → JWT token in response → use token in subsequent requests → 401 on invalid/expired token
- Role guards: GET /admin/users with cashier token → 403 Forbidden
- Tests: `pytest` passes; all auth, money math, role checks covered
- No debug prints; no `.env` in repo (`.env.example` only)

## Notes for Future Phases
- Phase 2: Products, suppliers, batches, inventory
  - Batch model with FEFO logic
  - Stock movement ledger
  - Low-stock and expiry alerts
- Phase 3: Billing engine, invoices, QR, public bill page
  - Invoice snapshot (copy product data)
  - Tax grouping by rate
  - Atomic transaction with rollback
- Phase 4: POS UI (keyboard-first)
  - Barcode input always focused
  - Cart with qty +/-, remove
  - Payment methods, change due
  - Print invoice with QR
- Phase 5: Customers, returns, voids, audit log
- Phase 6: Reports, seed demo, README walkthrough
