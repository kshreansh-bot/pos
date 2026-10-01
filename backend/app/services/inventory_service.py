"""Inventory service for stock management and FEFO logic."""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc
from app.models import StockBatch, Product, StockMovement, StockMovementType, User
from app.utils.errors import NotFoundError, ValidationError, StockError


class InventoryService:
    """Service for inventory and stock management with FEFO logic."""

    @staticmethod
    async def create_batch(
        session: AsyncSession,
        product_id: int,
        batch_number: str,
        quantity: int,
        purchase_price_paise: int,
        expiry_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> StockBatch:
        """Create a new stock batch.

        Business rules:
        - Batch number should be unique per product
        - Quantity must be positive
        """
        # Get product to verify it exists
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")

        if quantity <= 0:
            raise ValidationError("Batch quantity must be positive")

        batch = StockBatch(
            product_id=product_id,
            batch_number=batch_number,
            quantity=quantity,
            initial_quantity=quantity,
            purchase_price_paise=purchase_price_paise,
            expiry_date=expiry_date,
            is_active=True
        )

        session.add(batch)
        await session.flush()

        # Record stock movement (receipt)
        await InventoryService._record_movement(
            session=session,
            product_id=product_id,
            batch_id=batch.id,
            movement_type=StockMovementType.RECEIPT,
            quantity=quantity,
            quantity_before=0,
            quantity_after=quantity,
            reference_type="batch",
            reference_id=batch.id,
            user_id=user_id,
            reason="Stock received"
        )

        return batch

    @staticmethod
    async def get_available_stock(session: AsyncSession, product_id: int) -> int:
        """Get total available stock for a product (non-expired batches)."""
        result = await session.execute(
            select(StockBatch).where(
                and_(
                    StockBatch.product_id == product_id,
                    StockBatch.is_active == True,
                )
            )
        )
        batches = result.scalars().all()

        total = 0
        for batch in batches:
            if not batch.is_expired:
                total += batch.quantity

        return total

    @staticmethod
    async def get_fefo_batches(
        session: AsyncSession,
        product_id: int,
        quantity_needed: int
    ) -> List[tuple[StockBatch, int]]:
        """Get batches for FEFO (First Expiry First Out) stock allocation.

        Returns list of (batch, quantity_to_take) tuples.
        Business rules:
        - Sort by expiry date (nearest first)
        - Skip expired batches
        - Return batches until quantity_needed is met
        """
        result = await session.execute(
            select(StockBatch).where(
                and_(
                    StockBatch.product_id == product_id,
                    StockBatch.is_active == True,
                    StockBatch.quantity > 0
                )
            ).order_by(StockBatch.expiry_date)
        )
        batches = result.scalars().all()

        allocated = []
        remaining = quantity_needed

        for batch in batches:
            # Skip expired batches
            if batch.is_expired:
                continue

            # Allocate from this batch
            take = min(batch.quantity, remaining)
            allocated.append((batch, take))
            remaining -= take

            if remaining <= 0:
                break

        # Check if we have enough stock
        if remaining > 0:
            raise StockError(f"Insufficient stock for product {product_id}: needed {quantity_needed}, only {quantity_needed - remaining} available")

        return allocated

    @staticmethod
    async def deduct_stock(
        session: AsyncSession,
        product_id: int,
        quantity: int,
        reference_type: str,
        reference_id: int,
        user_id: int,
        reason: str = "Sale"
    ) -> List[tuple[StockBatch, int]]:
        """Deduct stock using FEFO logic.

        Returns list of (batch, quantity_deducted) tuples.
        """
        # Get FEFO batches
        batches_to_use = await InventoryService.get_fefo_batches(session, product_id, quantity)

        # Deduct from each batch and record movements
        for batch, qty_to_deduct in batches_to_use:
            quantity_before = batch.quantity
            batch.quantity -= qty_to_deduct
            quantity_after = batch.quantity

            await InventoryService._record_movement(
                session=session,
                product_id=product_id,
                batch_id=batch.id,
                movement_type=StockMovementType.SALE,
                quantity=-qty_to_deduct,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user_id,
                reason=reason
            )

        await session.flush()
        return batches_to_use

    @staticmethod
    async def adjust_stock(
        session: AsyncSession,
        product_id: int,
        adjustment_quantity: int,
        batch_id: Optional[int] = None,
        reason: str = "Manual adjustment",
        user_id: Optional[int] = None
    ) -> int:
        """Adjust stock (manual adjustment, positive or negative).

        Returns the new quantity.
        """
        if batch_id:
            # Adjust specific batch
            result = await session.execute(
                select(StockBatch).where(StockBatch.id == batch_id)
            )
            batch = result.scalar_one_or_none()
            if not batch:
                raise NotFoundError(f"Batch with ID {batch_id} not found")

            quantity_before = batch.quantity
            batch.quantity += adjustment_quantity
            quantity_after = batch.quantity

            await InventoryService._record_movement(
                session=session,
                product_id=product_id,
                batch_id=batch_id,
                movement_type=StockMovementType.ADJUSTMENT,
                quantity=adjustment_quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=reason,
                user_id=user_id
            )

            await session.flush()
            return batch.quantity
        else:
            # Adjust all active batches proportionally (or first batch)
            # For simplicity, adjust the first batch
            result = await session.execute(
                select(StockBatch).where(
                    and_(
                        StockBatch.product_id == product_id,
                        StockBatch.is_active == True
                    )
                ).order_by(StockBatch.expiry_date)
            )
            batches = result.scalars().all()

            if not batches:
                raise StockError(f"No active batches found for product {product_id}")

            batch = batches[0]
            quantity_before = batch.quantity
            batch.quantity += adjustment_quantity
            quantity_after = batch.quantity

            await InventoryService._record_movement(
                session=session,
                product_id=product_id,
                batch_id=batch.id,
                movement_type=StockMovementType.ADJUSTMENT,
                quantity=adjustment_quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=reason,
                user_id=user_id
            )

            await session.flush()
            return batch.quantity

    @staticmethod
    async def _record_movement(
        session: AsyncSession,
        product_id: int,
        batch_id: Optional[int],
        movement_type: StockMovementType,
        quantity: int,
        quantity_before: int,
        quantity_after: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> StockMovement:
        """Record a stock movement in the ledger."""
        movement = StockMovement(
            product_id=product_id,
            batch_id=batch_id,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            user_id=user_id or 1  # Default to system user if not provided
        )

        session.add(movement)
        await session.flush()
        return movement

    @staticmethod
    async def get_low_stock_items(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Product], int]:
        """Get products with stock below reorder level."""
        # Join Product with StockBatch to check stock levels
        result = await session.execute(
            select(Product).where(Product.is_active == True)
        )
        products = result.scalars().all()

        low_stock = []
        for product in products:
            # Get total stock for product
            stock = await InventoryService.get_available_stock(session, product.id)
            if stock <= product.reorder_level:
                low_stock.append(product)

        return low_stock[skip:skip+limit], len(low_stock)

    @staticmethod
    async def get_expiring_soon_items(
        session: AsyncSession,
        days: int = 7,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[StockBatch], int]:
        """Get batches expiring within N days."""
        cutoff = datetime.utcnow() + timedelta(days=days)

        result = await session.execute(
            select(StockBatch).where(
                and_(
                    StockBatch.expiry_date <= cutoff,
                    StockBatch.expiry_date > datetime.utcnow(),
                    StockBatch.is_active == True,
                    StockBatch.quantity > 0
                )
            ).order_by(StockBatch.expiry_date)
        )
        batches = result.scalars().all()

        return batches[skip:skip+limit], len(batches)


# Singleton instance
inventory_service = InventoryService()