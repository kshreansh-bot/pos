"""Main FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
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
allow_origins=[
"https://supermarket-billing-system-frontend.vercel.app",
"https://supermarket-billing-system-front-git-a54e3b-supermarket-billing.vercel.app",
"https://supermarket-billing-system-527-1txh.vercel.app",
],
allow_credentials=True,
allow_methods=[""],
allow_headers=[""],
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
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.environment}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }