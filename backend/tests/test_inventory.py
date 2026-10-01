"""Tests for inventory service with FEFO logic."""
import pytest
from datetime import datetime, timedelta
from app.services.inventory_service import inventory_service
from app.models import StockBatch, StockMovementType
from app.utils.errors import StockError, ValidationError


class TestInventoryService:
    """Test inventory service and FEFO logic."""

    @pytest.mark.asyncio
    async def test_create_batch(self, async_session):
        """Test creating a stock batch."""
        from app.models import Product, Category
        from sqlalchemy import select

        # Create category and product first
        category = Category(name="Test Category")
        async_session.add(category)
        await async_session.flush()

        product = Product(
            name="Test Product",
            category_id=category.id,
            unit="piece",
            mrp_paise=10000,
            purchase_price_paise=8000,
            selling_price_paise=10000,
            gst_rate=18
        )
        async_session.add(product)
        await async_session.flush()

        # Create batch
        batch = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="BATCH-001",
            quantity=100,
            purchase_price_paise=8000,
            user_id=1
        )

        assert batch.id is not None
        assert batch.quantity == 100
        assert batch.initial_quantity == 100

    @pytest.mark.asyncio
    async def test_fefo_allocation(self, async_session):
        """Test FEFO (First Expiry First Out) stock allocation."""
        from app.models import Product, Category

        # Create category and product
        category = Category(name="Test Category")
        async_session.add(category)
        await async_session.flush()

        product = Product(
            name="Test Product",
            category_id=category.id,
            unit="piece",
            mrp_paise=10000,
            purchase_price_paise=8000,
            selling_price_paise=10000,
            gst_rate=18
        )
        async_session.add(product)
        await async_session.flush()

        # Create batches with different expiry dates
        now = datetime.utcnow()

        batch1 = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="BATCH-001",
            quantity=50,
            purchase_price_paise=8000,
            expiry_date=now + timedelta(days=30),
            user_id=1
        )

        batch2 = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="BATCH-002",
            quantity=50,
            purchase_price_paise=8000,
            expiry_date=now + timedelta(days=10),  # Expires first
            user_id=1
        )

        # Get FEFO batches for 60 units
        fefo_batches = await inventory_service.get_fefo_batches(async_session, product.id, 60)

        # Should allocate from batch2 first (earlier expiry)
        assert len(fefo_batches) == 2
        assert fefo_batches[0][0].id == batch2.id
        assert fefo_batches[0][1] == 50
        assert fefo_batches[1][0].id == batch1.id
        assert fefo_batches[1][1] == 10

    @pytest.mark.asyncio
    async def test_expired_batch_blocked(self, async_session):
        """Test that expired batches are blocked from FEFO allocation."""
        from app.models import Product, Category

        category = Category(name="Test Category")
        async_session.add(category)
        await async_session.flush()

        product = Product(
            name="Test Product",
            category_id=category.id,
            unit="piece",
            mrp_paise=10000,
            purchase_price_paise=8000,
            selling_price_paise=10000,
            gst_rate=18
        )
        async_session.add(product)
        await async_session.flush()

        # Create expired batch
        batch_expired = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="EXPIRED",
            quantity=100,
            purchase_price_paise=8000,
            expiry_date=datetime.utcnow() - timedelta(days=1),
            user_id=1
        )

        # Create valid batch
        batch_valid = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="VALID",
            quantity=100,
            purchase_price_paise=8000,
            expiry_date=datetime.utcnow() + timedelta(days=30),
            user_id=1
        )

        # Try to allocate - should skip expired batch
        fefo_batches = await inventory_service.get_fefo_batches(async_session, product.id, 50)

        # Should only get from valid batch
        assert len(fefo_batches) == 1
        assert fefo_batches[0][0].id == batch_valid.id

    @pytest.mark.asyncio
    async def test_insufficient_stock_error(self, async_session):
        """Test error when insufficient stock."""
        from app.models import Product, Category

        category = Category(name="Test Category")
        async_session.add(category)
        await async_session.flush()

        product = Product(
            name="Test Product",
            category_id=category.id,
            unit="piece",
            mrp_paise=10000,
            purchase_price_paise=8000,
            selling_price_paise=10000,
            gst_rate=18
        )
        async_session.add(product)
        await async_session.flush()

        batch = await inventory_service.create_batch(
            async_session,
            product_id=product.id,
            batch_number="BATCH-001",
            quantity=50,
            purchase_price_paise=8000,
            user_id=1
        )

        # Try to allocate more than available
        with pytest.raises(StockError):
            await inventory_service.get_fefo_batches(async_session, product.id, 100)


@pytest.mark.asyncio
async def test_stock_movement_recorded(async_session):
    """Test that stock movements are recorded in ledger."""
    from app.models import Product, Category
    from sqlalchemy import select

    category = Category(name="Test Category")
    async_session.add(category)
    await async_session.flush()

    product = Product(
        name="Test Product",
        category_id=category.id,
        unit="piece",
        mrp_paise=10000,
        purchase_price_paise=8000,
        selling_price_paise=10000,
        gst_rate=18
    )
    async_session.add(product)
    await async_session.flush()

    # Create batch (should record receipt movement)
    batch = await inventory_service.create_batch(
        async_session,
        product_id=product.id,
        batch_number="BATCH-001",
        quantity=100,
        purchase_price_paise=8000,
        user_id=1
    )

    # Check movement was recorded
    from app.models import StockMovement
    result = await async_session.execute(
        select(StockMovement).where(
            StockMovement.product_id == product.id,
            StockMovement.movement_type == StockMovementType.RECEIPT
        )
    )
    movements = result.scalars().all()

    assert len(movements) == 1
    assert movements[0].quantity == 100
    assert movements[0].quantity_after == 100