"""Billing service for invoice creation and management."""
import secrets
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.models import (
    Invoice, InvoiceItem, InvoiceStatus, Product, StockBatch, StockMovement,
    StockMovementType, Customer, User, AuditLog
)
from app.utils.money import round_half_up, extract_gst_from_inclusive_price, paise_to_rupees
from app.utils.errors import StockError, ValidationError, AppException, NotFoundError
from typing import List, Tuple, Dict, Optional
import json


class BillingService:
    """Service for handling invoice creation and billing operations."""

    async def create_invoice(
        self,
        session: AsyncSession,
        user_id: int,
        items: List[Dict],  # [{product_id, quantity, discount_percent?}, ...]
        payment_method: str,
        customer_id: Optional[int] = None,
        discount_paise: int = 0,
        amount_tendered_paise: Optional[int] = None,
        loyalty_points_redeemed: int = 0,
    ) -> Invoice:
        """
        Create a new invoice with items, validate stock, and record movements.

        Atomic transaction: validate → create invoice → deduct stock → record movements.
        All-or-nothing: rollback on any failure.

        Args:
            session: Database session
            user_id: User creating the invoice (cashier)
            items: List of {product_id, quantity, discount_percent}
            payment_method: 'cash', 'card', or 'upi'
            customer_id: Optional customer ID
            discount_paise: Bill-level discount (applied to total)
            amount_tendered_paise: Amount paid by customer
            loyalty_points_redeemed: Loyalty points to redeem (1 point = ₹1 = 100 paise)

        Returns:
            Created invoice with all details

        Raises:
            StockError: If stock insufficient or expired
            ValidationError: If validation fails
        """
        try:
            # Validate payment method
            if payment_method not in ("cash", "card", "upi"):
                raise ValidationError(f"Invalid payment method: {payment_method}")

            if not items:
                raise ValidationError("Invoice must have at least one item")

            customer = None
            if customer_id:
                c_stmt = select(Customer).where(Customer.id == customer_id)
                c_res = await session.execute(c_stmt)
                customer = c_res.scalar_one_or_none()
                if not customer:
                    raise ValidationError(f"Customer {customer_id} not found")

                if loyalty_points_redeemed > 0:
                    if customer.loyalty_points < loyalty_points_redeemed:
                        raise ValidationError(
                            f"Insufficient loyalty points: has {customer.loyalty_points}, "
                            f"tried to redeem {loyalty_points_redeemed}"
                        )
                    # Convert 1 point = 100 paise (₹1)
                    loyalty_discount_paise = loyalty_points_redeemed * 100
                    discount_paise += loyalty_discount_paise
                    customer.loyalty_points -= loyalty_points_redeemed

            # Fetch all products and validate
            product_ids = [item["product_id"] for item in items]
            stmt = select(Product).where(Product.id.in_(product_ids))
            result = await session.execute(stmt)
            products_map = {p.id: p for p in result.scalars().all()}

            # Validate all products exist
            for item in items:
                if item["product_id"] not in products_map:
                    raise ValidationError(f"Product {item['product_id']} not found")

            # Step 1: Validate stock for all items (FEFO check)
            stock_allocation = []  # [(product_id, quantity, batches), ...]
            for item in items:
                product_id = item["product_id"]
                quantity = item["quantity"]

                if quantity <= 0:
                    raise ValidationError(f"Invalid quantity {quantity} for product {product_id}")

                # Get FEFO batches for this product
                batches = await self._get_fefo_batches(session, product_id, quantity)
                stock_allocation.append((product_id, quantity, batches))

            # Step 2: Calculate totals and build line items
            invoice_items_data = []
            subtotal_paise = 0
            total_tax_paise = 0

            for item_idx, item in enumerate(items):
                product = products_map[item["product_id"]]
                quantity = item["quantity"]
                discount_percent = item.get("discount_percent", 0)

                if discount_percent < 0 or discount_percent > 100:
                    raise ValidationError(f"Invalid discount percent: {discount_percent}")

                # Line calculation
                unit_price_paise = product.selling_price_paise
                line_gross_paise = unit_price_paise * quantity

                # Extract tax from inclusive price (returns tuple: base_price, tax_amount)
                base_paise, tax_amount_paise = extract_gst_from_inclusive_price(
                    line_gross_paise,
                    product.gst_rate
                )

                # Apply line discount
                line_discount_paise = round_half_up(
                    Decimal(line_gross_paise) * Decimal(discount_percent) / Decimal(100)
                )
                line_discount_paise = int(line_discount_paise)

                # Line total (inclusive, after discount)
                line_total_paise = line_gross_paise - line_discount_paise

                subtotal_paise += line_gross_paise
                total_tax_paise += tax_amount_paise

                invoice_items_data.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_barcode": product.barcode,
                    "product_unit": product.unit,
                    "quantity": quantity,
                    "unit_price_paise": unit_price_paise,
                    "gst_rate": product.gst_rate,
                    "discount_percent": discount_percent,
                    "discount_paise": line_discount_paise,
                    "tax_amount_paise": tax_amount_paise,
                    "line_total_paise": line_total_paise,
                    "batches": stock_allocation[item_idx][2],
                })

            # Step 3: Calculate final totals
            total_amount_paise = subtotal_paise - discount_paise - total_tax_paise

            if total_amount_paise < 0:
                total_amount_paise = 0

            # Validate payment
            if amount_tendered_paise is not None:
                if amount_tendered_paise < total_amount_paise:
                    raise ValidationError(
                        f"Insufficient payment: need {paise_to_rupees(total_amount_paise)}, "
                        f"got {paise_to_rupees(amount_tendered_paise)}"
                    )

            change_due_paise = None
            if amount_tendered_paise is not None:
                change_due_paise = amount_tendered_paise - total_amount_paise

            # Step 4: Generate public token (random 128-bit, not sequential)
            public_token = self.generate_public_token()

            # Step 5: Generate invoice number (INV-YYYY-XXXXXX)
            invoice_number = await self._generate_invoice_number(session)

            # Step 6: Create invoice record
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_id=customer_id,
                user_id=user_id,
                subtotal_paise=subtotal_paise,
                total_discount_paise=discount_paise,
                total_tax_paise=total_tax_paise,
                total_amount_paise=total_amount_paise,
                payment_method=payment_method,
                amount_tendered_paise=amount_tendered_paise,
                change_due_paise=change_due_paise,
                status=InvoiceStatus.COMPLETED,
                public_token=public_token,
            )
            session.add(invoice)
            await session.flush()

            # Step 7: Create invoice items and deduct stock
            for item_data in invoice_items_data:
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=item_data["product_id"],
                    product_name=item_data["product_name"],
                    product_barcode=item_data["product_barcode"],
                    product_unit=item_data["product_unit"],
                    quantity=item_data["quantity"],
                    unit_price_paise=item_data["unit_price_paise"],
                    gst_rate=item_data["gst_rate"],
                    discount_percent=item_data["discount_percent"],
                    discount_paise=item_data["discount_paise"],
                    tax_amount_paise=item_data["tax_amount_paise"],
                    line_total_paise=item_data["line_total_paise"],
                )
                session.add(invoice_item)

                # Deduct from batches using FEFO
                remaining_qty = item_data["quantity"]
                for batch, batch_qty in item_data["batches"]:
                    qty_to_take = min(remaining_qty, batch_qty)

                    # Record stock movement
                    movement = StockMovement(
                        product_id=item_data["product_id"],
                        batch_id=batch.id,
                        movement_type=StockMovementType.SALE,
                        quantity=-qty_to_take,
                        quantity_before=batch.quantity,
                        quantity_after=batch.quantity - qty_to_take,
                        reference_type="invoice",
                        reference_id=invoice.id,
                        reason=f"Sale: {invoice_number}",
                        user_id=user_id,
                    )
                    session.add(movement)

                    # Update batch quantity
                    batch.quantity -= qty_to_take

                    # Update invoice item batch reference (first batch)
                    if invoice_item.batch_id is None:
                        invoice_item.batch_id = batch.id

                    remaining_qty -= qty_to_take
                    if remaining_qty == 0:
                        break

            # Step 8: Add loyalty points earned
            if customer:
                # Earn 1 point for every ₹100 spent on final net total
                points_earned = total_amount_paise // (100 * 100)
                if points_earned > 0:
                    customer.loyalty_points += points_earned
                # We already deducted the redeemed points upfront

            await session.flush()
            await session.commit()

            # Reload with items and customer eagerly loaded
            stmt = select(Invoice).options(
                selectinload(Invoice.items),
                selectinload(Invoice.customer)
            ).where(Invoice.id == invoice.id)
            result = await session.execute(stmt)
            return result.scalar_one()

        except Exception as e:
            await session.rollback()
            raise

    def generate_public_token(self) -> str:
        """Generate random 128-bit token for public bill page (not sequential, not invoice ID).

        Returns:
            Hex string of 128 bits (32 hex characters)
        """
        return secrets.token_hex(16)  # 16 bytes = 128 bits = 32 hex chars

    async def _generate_invoice_number(self, session: AsyncSession) -> str:
        """Generate sequential invoice number per year (INV-YYYY-XXXXXX).

        Args:
            session: Database session

        Returns:
            Invoice number string

        Raises:
            AppException: If unable to generate invoice number
        """
        try:
            current_year = datetime.utcnow().year

            # Count existing invoices for this year
            # Use a database-agnostic approach: extract year from created_at
            result = await session.execute(
                select(func.count(Invoice.id)).where(
                    and_(
                        Invoice.created_at >= datetime(current_year, 1, 1),
                        Invoice.created_at < datetime(current_year + 1, 1, 1)
                    )
                )
            )
            invoice_count = result.scalar() or 0
            invoice_number = f"INV-{current_year}-{str(invoice_count + 1).zfill(6)}"
            return invoice_number
        except Exception as e:
            raise AppException(f"Failed to generate invoice number: {str(e)}")

    def calculate_invoice_totals(
        self,
        items_with_tax: List[InvoiceItem]
    ) -> Tuple[int, int, int]:
        """Calculate invoice totals from items with tax information.

        Args:
            items_with_tax: List of InvoiceItem objects with tax calculated

        Returns:
            Tuple of (subtotal_paise, total_tax_paise, total_amount_paise)
        """
        subtotal_paise = 0
        total_tax_paise = 0
        total_amount_paise = 0

        for item in items_with_tax:
            # Base amount (before discount)
            base_paise = item.line_total_paise - item.tax_amount_paise

            subtotal_paise += item.unit_price_paise * item.quantity
            total_tax_paise += item.tax_amount_paise
            total_amount_paise += item.line_total_paise - item.discount_paise

        return subtotal_paise, total_tax_paise, total_amount_paise

    async def get_invoice_by_token(
        self,
        session: AsyncSession,
        public_token: str
    ) -> Optional[Invoice]:
        """Retrieve invoice by public token for public bill page.

        Args:
            session: Database session
            public_token: Public token (128-bit random hex)

        Returns:
            Invoice with all items and customer info, or None if not found
        """
        stmt = select(Invoice).options(
            selectinload(Invoice.items),
            selectinload(Invoice.customer)
        ).where(Invoice.public_token == public_token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_invoice_by_id(
        self,
        session: AsyncSession,
        invoice_id: int
    ) -> Optional[Invoice]:
        """Retrieve invoice by ID.

        Args:
            session: Database session
            invoice_id: Invoice ID

        Returns:
            Invoice object or None if not found
        """
        stmt = select(Invoice).options(
            selectinload(Invoice.items),
            selectinload(Invoice.customer)
        ).where(Invoice.id == invoice_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def group_tax_by_rate(self, items: List[InvoiceItem]) -> Dict[int, Dict]:
        """Group invoice items by GST rate for tax summary.

        Args:
            items: List of InvoiceItem objects

        Returns:
            {gst_rate: {"base_amount_paise": ..., "tax_amount_paise": ..., "total_paise": ...}, ...}
        """
        grouped = {}
        for item in items:
            rate = item.gst_rate
            if rate not in grouped:
                grouped[rate] = {
                    "base_amount_paise": 0,
                    "tax_amount_paise": 0,
                    "total_paise": 0,
                }

            # Calculate base (without tax)
            base_paise = item.line_total_paise - item.tax_amount_paise

            grouped[rate]["base_amount_paise"] += base_paise
            grouped[rate]["tax_amount_paise"] += item.tax_amount_paise
            grouped[rate]["total_paise"] += item.line_total_paise

        return grouped

    async def cancel_invoice(
        self,
        session: AsyncSession,
        invoice_id: int,
        user_id: int,
        reason: str
    ) -> Invoice:
        """Cancel an invoice and reverse stock movements.

        Atomic transaction: mark cancelled → reverse all stock movements.

        Args:
            session: Database session
            invoice_id: Invoice to cancel
            user_id: User cancelling the invoice
            reason: Reason for cancellation

        Returns:
            Cancelled invoice

        Raises:
            ValidationError: If invoice not found or already cancelled
        """
        try:
            invoice = await self.get_invoice_by_id(session, invoice_id)
            if not invoice:
                raise ValidationError(f"Invoice {invoice_id} not found")

            if invoice.status == InvoiceStatus.CANCELLED:
                raise ValidationError(f"Invoice {invoice_id} already cancelled")

            # Reverse all stock movements
            stmt = select(StockMovement).where(
                and_(
                    StockMovement.reference_type == "invoice",
                    StockMovement.reference_id == invoice_id,
                    StockMovement.movement_type == StockMovementType.SALE
                )
            )
            result = await session.execute(stmt)
            sale_movements = result.scalars().all()

            for movement in sale_movements:
                # Restore batch quantity
                stmt = select(StockBatch).where(StockBatch.id == movement.batch_id)
                result = await session.execute(stmt)
                batch = result.scalar_one()

                quantity_before = batch.quantity
                qty_to_restore = abs(movement.quantity)
                batch.quantity += qty_to_restore
                quantity_after = batch.quantity

                # Create reversal movement
                reversal = StockMovement(
                    product_id=movement.product_id,
                    batch_id=batch.id,
                    movement_type=StockMovementType.VOID,
                    quantity=qty_to_restore,  # Positive reversal
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    reference_type="invoice_cancellation",
                    reference_id=invoice_id,
                    reason=f"Cancellation: {reason}",
                    user_id=user_id,
                )
                session.add(reversal)

            # Create audit log
            audit_log = AuditLog(
                user_id=user_id,
                action="cancelled",
                entity_type="invoice",
                entity_id=invoice_id,
                new_values=json.dumps({"status": InvoiceStatus.CANCELLED.value, "reason": reason}),
                reason=reason
            )
            session.add(audit_log)

            # Mark invoice as cancelled
            invoice.status = InvoiceStatus.CANCELLED
            invoice.notes = reason

            await session.flush()
            await session.commit()

            stmt = select(Invoice).options(
                selectinload(Invoice.items),
                selectinload(Invoice.customer)
            ).where(Invoice.id == invoice.id)
            result = await session.execute(stmt)
            return result.scalar_one()

        except Exception as e:
            await session.rollback()
            raise

    async def process_return(
        self,
        session: AsyncSession,
        invoice_id: int,
        user_id: int,
        returned_items: List[Dict],  # [{product_id, invoice_item_id, quantity, reason}, ...]
        reason: str = "Customer return"
    ) -> Invoice:
        """Process a partial or full return for an invoice.

        Creates return invoice and reverses stock for returned items.

        Args:
            session: Database session
            invoice_id: Original invoice ID
            user_id: User processing the return
            returned_items: List of {product_id, invoice_item_id, quantity, reason}
            reason: Overall reason for return

        Returns:
            Return invoice record

        Raises:
            ValidationError: If invoice not found or return is invalid
            StockError: If unable to reverse stock
        """
        try:
            # Get original invoice
            original_invoice = await self.get_invoice_by_id(session, invoice_id)
            if not original_invoice:
                raise ValidationError(f"Invoice {invoice_id} not found")

            if original_invoice.status != InvoiceStatus.COMPLETED:
                raise ValidationError(
                    f"Cannot return from invoice with status {original_invoice.status.value}"
                )

            # Validate all returned items
            stmt = select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
            result = await session.execute(stmt)
            original_items_map = {item.id: item for item in result.scalars().all()}

            return_amount_paise = 0
            return_tax_paise = 0

            for return_item in returned_items:
                invoice_item_id = return_item.get("invoice_item_id")
                qty_returned = return_item.get("quantity", 0)

                if invoice_item_id not in original_items_map:
                    raise ValidationError(f"Item {invoice_item_id} not found in invoice")

                original_item = original_items_map[invoice_item_id]

                if qty_returned <= 0 or qty_returned > original_item.quantity:
                    raise ValidationError(
                        f"Invalid return quantity {qty_returned} for item {invoice_item_id}"
                    )

                # Calculate return amount (pro-rata)
                item_return_amount = (original_item.line_total_paise * qty_returned) // original_item.quantity
                item_return_tax = (original_item.tax_amount_paise * qty_returned) // original_item.quantity

                return_amount_paise += item_return_amount
                return_tax_paise += item_return_tax

                # Reverse stock for this item
                if original_item.batch_id:
                    stmt = select(StockBatch).where(StockBatch.id == original_item.batch_id)
                    result = await session.execute(stmt)
                    batch = result.scalar_one_or_none()

                    if batch:
                        quantity_before = batch.quantity
                        batch.quantity += qty_returned

                        # Record return movement
                        movement = StockMovement(
                            product_id=original_item.product_id,
                            batch_id=batch.id,
                            movement_type=StockMovementType.RETURN,
                            quantity=qty_returned,
                            quantity_before=quantity_before,
                            quantity_after=batch.quantity,
                            reference_type="return",
                            reference_id=invoice_id,
                            reason=f"Return: {return_item.get('reason', reason)}",
                            user_id=user_id,
                        )
                        session.add(movement)

            # Create return invoice
            return_invoice = Invoice(
                invoice_number=f"{original_invoice.invoice_number}-RET",
                customer_id=original_invoice.customer_id,
                user_id=user_id,
                subtotal_paise=return_amount_paise,
                total_discount_paise=0,
                total_tax_paise=return_tax_paise,
                total_amount_paise=return_amount_paise - return_tax_paise,
                payment_method=original_invoice.payment_method,
                amount_tendered_paise=return_amount_paise - return_tax_paise,
                change_due_paise=0,
                status=InvoiceStatus.RETURNED,
                public_token=self.generate_public_token(),
                notes=reason,
            )
            session.add(return_invoice)

            # Create audit log
            audit_log = AuditLog(
                user_id=user_id,
                action="return_processed",
                entity_type="invoice",
                entity_id=invoice_id,
                new_values=json.dumps({
                    "return_invoice_number": return_invoice.invoice_number,
                    "items_returned": len(returned_items),
                    "amount_refunded": return_amount_paise
                }),
                reason=reason
            )
            session.add(audit_log)

            await session.flush()
            await session.commit()

            stmt = select(Invoice).options(
                selectinload(Invoice.items),
                selectinload(Invoice.customer)
            ).where(Invoice.id == return_invoice.id)
            result = await session.execute(stmt)
            return result.scalar_one()

        except Exception as e:
            await session.rollback()
            raise

    async def _get_fefo_batches(
        self,
        session: AsyncSession,
        product_id: int,
        quantity_needed: int
    ) -> List[Tuple[StockBatch, int]]:
        """Get FEFO (First Expiry First Out) batches for a product.

        Returns list of (batch, quantity_to_take) tuples ordered by expiry date.

        Args:
            session: Database session
            product_id: Product ID
            quantity_needed: Quantity needed

        Returns:
            List of (batch, quantity_to_take) tuples

        Raises:
            StockError: If insufficient or expired stock
        """
        # Query non-expired active batches, ordered by expiry date
        stmt = select(StockBatch).where(
            and_(
                StockBatch.product_id == product_id,
                StockBatch.is_active == True,
                StockBatch.quantity > 0,
            )
        ).order_by(StockBatch.expiry_date.asc())

        result = await session.execute(stmt)
        batches = result.scalars().all()

        # Filter out expired batches
        current_time = datetime.utcnow()
        available_batches = [
            b for b in batches
            if b.expiry_date is None or b.expiry_date >= current_time
        ]

        if not available_batches:
            raise StockError(
                f"No available stock for product {product_id} (all expired or out of stock)"
            )

        # Allocate from batches
        allocation = []
        remaining = quantity_needed

        for batch in available_batches:
            if remaining <= 0:
                break

            qty_to_take = min(remaining, batch.quantity)
            allocation.append((batch, qty_to_take))
            remaining -= qty_to_take

        if remaining > 0:
            raise StockError(
                f"Insufficient stock for product {product_id}: need {quantity_needed}, "
                f"available {quantity_needed - remaining}"
            )

        return allocation


# Global instance
billing_service = BillingService()
