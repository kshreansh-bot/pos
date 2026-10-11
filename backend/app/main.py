import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )
"""Main FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database import async_session_maker, init_db
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.errors import AppException
from app.api import auth, users, products, suppliers, inventory, invoices, public, customers, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup if needed


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Supermarket POS & Inventory System API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error": exc.__class__.__name__}
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(inventory.router)
app.include_router(invoices.router)
app.include_router(customers.router)
app.include_router(reports.router)
app.include_router(public.router)


@app.get("/health")
async def health_check():
    """Health check including the database connection and basic row counts."""
    try:
        async with async_session_maker() as session:
            products = (await session.execute(text("SELECT COUNT(*) FROM products"))).scalar_one()
            invoices = (await session.execute(text("SELECT COUNT(*) FROM invoices"))).scalar_one()
            customers = (await session.execute(text("SELECT COUNT(*) FROM customers"))).scalar_one()
        return {
            "status": "healthy",
            "environment": settings.environment,
            "database": "connected",
            "counts": {"products": products, "invoices": invoices, "customers": customers},
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "environment": settings.environment, "database": "error", "detail": str(exc)},
        )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }