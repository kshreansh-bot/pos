"""Product service with business logic for the Supermarket POS system."""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from app.models import Product, Category, Supplier, StockBatch, UserRole
from app.schemas import UserResponse
from app.utils.errors import NotFoundError, ValidationError, BusinessRuleError
from app.utils.money import paise_to_rupees, rupees_to_paise


class ProductService:
    """Service for product management and business logic."""

    @staticmethod
    async def create_product(
        session: AsyncSession,
        name: str,
        category_id: int,
        unit: str,
        mrp_paise: int,
        purchase_price_paise: int,
        selling_price_paise: int,
        gst_rate: int,
        barcode: Optional[str] = None,
        brand: Optional[str] = None,
        reorder_level: int = 10,
        supplier_id: Optional[int] = None,
        default_discount_percent: int = 0,
    ) -> Product:
        """Create a new product.

        Business rules:
        - Barcode must be unique if provided
        - Selling price must be <= MRP
        - GST rate must be valid (0, 5, 12, 18, 28)
        """
        # Validate business rules
        if selling_price_paise > mrp_paise:
            raise ValidationError("Selling price cannot exceed MRP")

        if gst_rate not in [0, 5, 12, 18, 28]:
            raise ValidationError("GST rate must be one of: 0, 5, 12, 18, 28")

        if default_discount_percent < 0 or default_discount_percent > 100:
            raise ValidationError("Discount percent must be between 0 and 100")

        # Check barcode uniqueness if provided
        if barcode:
            result = await session.execute(
                select(Product).where(Product.barcode == barcode)
            )
            if result.scalar_one_or_none():
                raise ValidationError(f"Barcode '{barcode}' already exists")

        # Check category exists
        result = await session.execute(select(Category).where(Category.id == category_id))
        if not result.scalar_one_or_none():
            raise NotFoundError(f"Category with ID {category_id} not found")

        # Create product
        product = Product(
            barcode=barcode,
            name=name,
            brand=brand,
            category_id=category_id,
            unit=unit,
            mrp_paise=mrp_paise,
            purchase_price_paise=purchase_price_paise,
            selling_price_paise=selling_price_paise,
            gst_rate=gst_rate,
            reorder_level=reorder_level,
            supplier_id=supplier_id,
            default_discount_percent=default_discount_percent,
            is_active=True
        )

        session.add(product)
        await session.flush()
        return product

    @staticmethod
    async def get_product(session: AsyncSession, product_id: int) -> Product:
        """Get product by ID."""
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")
        return product

    @staticmethod
    async def get_product_by_barcode(session: AsyncSession, barcode: str) -> Optional[Product]:
        """Get product by barcode."""
        result = await session.execute(
            select(Product).where(Product.barcode == barcode)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def search_products(
        session: AsyncSession,
        query: Optional[str] = None,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Product], int]:
        """Search products by query (barcode, name, brand) and category.

        Returns: (products, total_count)
        """
        base_query = select(Product).where(Product.is_active == True)

        if query:
            search_term = f"%{query}%"
            base_query = base_query.where(
                or_(
                    Product.barcode.ilike(search_term),
                    Product.name.ilike(search_term),
                    Product.brand.ilike(search_term),
                )
            )

        if category_id:
            base_query = base_query.where(Product.category_id == category_id)

        # Get total count
        count_query = select(Product).where(Product.is_active == True)
        if query:
            search_term = f"%{query}%"
            count_query = count_query.where(
                or_(
                    Product.barcode.ilike(search_term),
                    Product.name.ilike(search_term),
                    Product.brand.ilike(search_term),
                )
            )
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)

        count_result = await session.execute(count_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await session.execute(
            base_query.order_by(Product.name).offset(skip).limit(limit)
        )
        products = result.scalars().all()

        return products, total

    @staticmethod
    async def get_low_stock_items(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Product], int]:
        """Get products below reorder level."""
        # This would need a calculated field for current stock
        # For now, return products that have reorder_level set
        query = select(Product).where(Product.is_active == True)
        result = await session.execute(query)
        products = result.scalars().all()

        # Filter to low stock (would need inventory service to calculate)
        return products[:limit], len(products)

    @staticmethod
    async def update_product(
        session: AsyncSession,
        product_id: int,
        **kwargs
    ) -> Product:
        """Update product fields."""
        product = await ProductService.get_product(session, product_id)

        # Validate business rules
        if "selling_price_paise" in kwargs and "mrp_paise" in kwargs:
            if kwargs["selling_price_paise"] > kwargs["mrp_paise"]:
                raise ValidationError("Selling price cannot exceed MRP")
        elif "selling_price_paise" in kwargs:
            if kwargs["selling_price_paise"] > product.mrp_paise:
                raise ValidationError("Selling price cannot exceed MRP")

        if "gst_rate" in kwargs:
            if kwargs["gst_rate"] not in [0, 5, 12, 18, 28]:
                raise ValidationError("GST rate must be one of: 0, 5, 12, 18, 28")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        await session.flush()
        return product

    @staticmethod
    async def deactivate_product(session: AsyncSession, product_id: int) -> Product:
        """Deactivate product (soft delete)."""
        product = await ProductService.get_product(session, product_id)
        product.is_active = False
        await session.flush()
        return product


# Singleton instance
product_service = ProductService()