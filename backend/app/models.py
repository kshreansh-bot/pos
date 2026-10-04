"""Database models using SQLAlchemy 2.0."""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, ForeignKey,
    Index, UniqueConstraint, CheckConstraint, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    INVENTORY_MANAGER = "inventory_manager"
    CUSTOMER = "customer"


class User(Base):
    """User model for authentication and access control."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.CASHIER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_discount_percent: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="user", lazy="selectin")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"


class Category(Base):
    """Product category model."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="category", lazy="selectin")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Supplier(Base):
    """Supplier/vendor model."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    purchases = relationship("Purchase", back_populates="supplier", lazy="selectin")
    products = relationship("Product", back_populates="supplier", lazy="selectin")

    def __repr__(self):
        return f"<Supplier(id={self.id}, name={self.name})>"


class Product(Base):
    """Product model with inventory tracking."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("barcode", name="uq_product_barcode"),
        CheckConstraint("selling_price_paise >= 0", name="ck_selling_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="piece")  # piece, kg, liter, etc.

    # Prices stored as paise (integer)
    mrp_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    selling_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # GST rate as percentage (0, 5, 12, 18, 28)
    gst_rate: Mapped[int] = mapped_column(Integer, default=18)

    # Inventory settings
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    default_discount_percent: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    batches = relationship("StockBatch", back_populates="product", lazy="selectin")
    invoice_items = relationship("InvoiceItem", back_populates="product", lazy="selectin")
    purchase_items = relationship("PurchaseItem", back_populates="product", lazy="selectin")
    stock_movements = relationship("StockMovement", back_populates="product", lazy="selectin")

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, barcode={self.barcode})>"


class StockBatch(Base):
    """Stock batch model for inventory tracking with expiry (FEFO)."""

    __tablename__ = "stock_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    batch_number: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # Current quantity in stock
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # Original quantity
    purchase_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="batches")
    stock_movements = relationship("StockMovement", back_populates="batch", lazy="selectin")

    # Index for FEFO queries
    __table_args__ = (
        Index("ix_stock_batch_fefo", "product_id", "expiry_date", "is_active"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if batch is expired."""
        if self.expiry_date is None:
            return False
        return datetime.utcnow() > self.expiry_date

    @property
    def is_expiring_soon(self, days: int = 7) -> bool:
        """Check if batch is expiring within given days."""
        if self.expiry_date is None:
            return False
        from datetime import timedelta
        return datetime.utcnow() + timedelta(days=days) > self.expiry_date

    def __repr__(self):
        return f"<StockBatch(id={self.id}, product_id={self.product_id}, batch={self.batch_number}, qty={self.quantity})>"


class StockMovementType(str, Enum):
    """Types of stock movements."""
    RECEIPT = "receipt"           # Stock received from supplier
    SALE = "sale"                 # Stock sold
    ADJUSTMENT = "adjustment"     # Manual adjustment (with reason)
    RETURN = "return"             # Customer return
    VOID = "void"                 # Voided sale


class StockMovement(Base):
    """Stock movement ledger for audit trail."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stock_batches.id"), nullable=True)
    movement_type: Mapped[StockMovementType] = mapped_column(
        SQLEnum(StockMovementType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # Positive for in, negative for out
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # purchase, invoice, etc.
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    product = relationship("Product", back_populates="stock_movements")
    batch = relationship("StockBatch", back_populates="stock_movements")
    user = relationship("User")

    def __repr__(self):
        return f"<StockMovement(id={self.id}, type={self.movement_type.value}, qty={self.quantity})>"


class Purchase(Base):
    """Purchase order from supplier."""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    purchase_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # pending, completed, cancelled
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchases")
    user = relationship("User")
    items = relationship("PurchaseItem", back_populates="purchase", lazy="selectin")

    def __repr__(self):
        return f"<Purchase(id={self.id}, invoice={self.invoice_number})>"


class PurchaseItem(Base):
    """Items in a purchase order."""

    __tablename__ = "purchase_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_rate: Mapped[int] = mapped_column(Integer, default=18)
    total_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")

    def __repr__(self):
        return f"<PurchaseItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"


class Customer(Base):
    """Customer model for loyalty and billing."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="customer", lazy="selectin")

    def __repr__(self):
        return f"<Customer(id={self.id}, name={self.name}, phone={self.phone})>"


class InvoiceStatus(str, Enum):
    """Invoice status values."""
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Invoice(Base):
    """Invoice model - the core billing document."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoice_number_year", "invoice_number", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Links to related entities
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Financial summary (all in paise)
    subtotal_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    total_discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_tax_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # Payment details
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)  # cash, card, upi
    amount_tendered_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    change_due_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status and metadata
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=InvoiceStatus.COMPLETED
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Public token for QR code (random 128-bit, not sequential)
    public_token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    user = relationship("User", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", lazy="selectin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, status={self.status.value})>"


class InvoiceItem(Base):
    """Invoice line items with snapshot data."""

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    # Snapshot fields - copied at time of sale to prevent retroactive changes
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_unit: Mapped[str] = mapped_column(String(20), default="piece")

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # All prices in paise
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)  # Selling price (GST inclusive)
    gst_rate: Mapped[int] = mapped_column(Integer, default=18)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)

    # Tax extracted from inclusive price
    tax_amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # Line total
    line_total_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # Stock batch used (for FEFO tracking)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stock_batches.id"), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")
    batch = relationship("StockBatch")

    def __repr__(self):
        return f"<InvoiceItem(id={self.id}, product={self.product_name}, qty={self.quantity})>"


class AuditLog(Base):
    """Audit log for tracking changes."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, product, invoice, etc.
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    old_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    new_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type}:{self.entity_id})>"