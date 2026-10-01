"""Supplier service for the Supermarket POS system."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from app.models import Supplier
from app.utils.errors import NotFoundError, ValidationError


class SupplierService:
    """Service for supplier management."""

    @staticmethod
    async def create_supplier(
        session: AsyncSession,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        gst_number: Optional[str] = None,
    ) -> Supplier:
        """Create a new supplier.

        Business rules:
        - GST number format: 15 alphanumeric characters (Indian format)
        """
        # Validate GST number if provided
        if gst_number:
            if len(gst_number) != 15 or not gst_number.replace("-", "").isalnum():
                raise ValidationError("Invalid GST number format (expected 15 alphanumeric characters)")

        supplier = Supplier(
            name=name,
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address,
            gst_number=gst_number,
            is_active=True
        )

        session.add(supplier)
        await session.flush()
        return supplier

    @staticmethod
    async def get_supplier(session: AsyncSession, supplier_id: int) -> Supplier:
        """Get supplier by ID."""
        result = await session.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise NotFoundError(f"Supplier with ID {supplier_id} not found")
        return supplier

    @staticmethod
    async def search_suppliers(
        session: AsyncSession,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Supplier], int]:
        """Search suppliers by name, contact person, or phone."""
        base_query = select(Supplier).where(Supplier.is_active == True)

        if query:
            search_term = f"%{query}%"
            base_query = base_query.where(
                or_(
                    Supplier.name.ilike(search_term),
                    Supplier.contact_person.ilike(search_term),
                    Supplier.phone.ilike(search_term),
                )
            )

        # Get total count
        count_result = await session.execute(base_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await session.execute(
            base_query.order_by(Supplier.name).offset(skip).limit(limit)
        )
        suppliers = result.scalars().all()

        return suppliers, total

    @staticmethod
    async def update_supplier(
        session: AsyncSession,
        supplier_id: int,
        **kwargs
    ) -> Supplier:
        """Update supplier fields."""
        supplier = await SupplierService.get_supplier(session, supplier_id)

        # Validate GST number if provided
        if "gst_number" in kwargs and kwargs["gst_number"]:
            gst = kwargs["gst_number"]
            if len(gst) != 15 or not gst.replace("-", "").isalnum():
                raise ValidationError("Invalid GST number format")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)

        await session.flush()
        return supplier

    @staticmethod
    async def deactivate_supplier(session: AsyncSession, supplier_id: int) -> Supplier:
        """Deactivate supplier (soft delete)."""
        supplier = await SupplierService.get_supplier(session, supplier_id)
        supplier.is_active = False
        await session.flush()
        return supplier


# Singleton instance
supplier_service = SupplierService()