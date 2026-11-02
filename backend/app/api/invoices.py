"""API routes for invoice management."""
from fastapi import APIRouter, Depends, Header, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db_session
from app.models import UserRole, Invoice, InvoiceItem
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.services.billing_service import billing_service
from app.services.qr_service import qr_service
from app.utils.errors import AppException, AuthorizationError, ValidationError
from app.utils.money import paise_to_rupees
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# Schemas
class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int
    discount_percent: int = 0


class InvoiceCreate(BaseModel):
    items: List[InvoiceItemCreate]
    customer_id: Optional[int] = None
    payment_method: str  # cash, card, upi
    discount_paise: int = 0
    amount_tendered_paise: Optional[int] = None
    loyalty_points_redeemed: int = 0


class InvoiceItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_barcode: Optional[str]
    product_unit: str
    quantity: int
    unit_price_paise: int
    gst_rate: int
    discount_percent: int
    discount_paise: int
    tax_amount_paise: int
    line_total_paise: int

    class Config:
        from_attributes = True


class TaxGroupResponse(BaseModel):
    gst_rate: int
    base_amount_paise: int
    tax_amount_paise: int
    total_paise: int


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_id: Optional[int]
    user_id: int
    subtotal_paise: int
    total_discount_paise: int
    total_tax_paise: int
    total_amount_paise: int
    payment_method: str
    amount_tendered_paise: Optional[int]
    change_due_paise: Optional[int]
    status: str
    public_token: str
    items: List[InvoiceItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceCancelRequest(BaseModel):
    reason: str


async def require_role_for_invoices(
    required_roles: List[UserRole],
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Dependency to check user role for invoice endpoints."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    if user.role not in required_roles:
        raise AuthorizationError("Insufficient permissions for this operation")

    return user
async def get_current_invoice_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await require_role_for_invoices(
        [UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN],
        authorization,
        session,
    )


@router.post("/create", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_create: InvoiceCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_invoice_user),
     

):
    """Create a new invoice (cashier, manager, admin only)."""
    items = [item.model_dump() for item in invoice_create.items]

    invoice = await billing_service.create_invoice(
        session,
        user_id=current_user.id,
        items=items,
        payment_method=invoice_create.payment_method,
        customer_id=invoice_create.customer_id,
        discount_paise=invoice_create.discount_paise,
        amount_tendered_paise=invoice_create.amount_tendered_paise,
        loyalty_points_redeemed=invoice_create.loyalty_points_redeemed,
    )

    return InvoiceResponse.model_validate(invoice)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
):
    """Get invoice by ID (any authenticated user)."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    invoice = await billing_service.get_invoice_by_id(session, invoice_id)
    if not invoice:
        raise AppException("Invoice not found", status_code=404)

    return InvoiceResponse.model_validate(invoice)


@router.get("/", response_model=dict)
async def list_invoices(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cashier_id: Optional[int] = None,
):
    """List invoices with pagination and filtering."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    # Build query
    query = select(Invoice)

    # Cashiers can only see their own invoices
    if user.role == UserRole.CASHIER:
        query = query.where(Invoice.user_id == user_id)

    # Filter by cashier if specified (admin/manager only)
    if cashier_id and user.role in (UserRole.ADMIN, UserRole.MANAGER):
        query = query.where(Invoice.user_id == cashier_id)

    # Date range filter
    if start_date:
        query = query.where(Invoice.created_at >= start_date)
    if end_date:
        query = query.where(Invoice.created_at <= end_date)

    # Execute query with pagination
    query = query.offset(skip).limit(limit).order_by(Invoice.created_at.desc())
    result = await session.execute(query)
    invoices = result.scalars().all()

    # Get total count
    count_query = select(Invoice)
    if user.role == UserRole.CASHIER:
        count_query = count_query.where(Invoice.user_id == user_id)
    if cashier_id and user.role in (UserRole.ADMIN, UserRole.MANAGER):
        count_query = count_query.where(Invoice.user_id == cashier_id)
    if start_date:
        count_query = count_query.where(Invoice.created_at >= start_date)
    if end_date:
        count_query = count_query.where(Invoice.created_at <= end_date)

    from sqlalchemy import func
    count_result = await session.execute(select(func.count(Invoice.id)).select_from(Invoice).where(count_query.whereclause))
    total = count_result.scalar() or 0

    return {
        "items": [InvoiceResponse.model_validate(i) for i in invoices],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: int,
    cancel_request: InvoiceCancelRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_invoices([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Cancel an invoice (admin, manager only)."""
    invoice = await billing_service.cancel_invoice(
        session,
        invoice_id=invoice_id,
        user_id=current_user.id,
        reason=cancel_request.reason,
    )

    return InvoiceResponse.model_validate(invoice)


@router.get("/{invoice_id}/print", response_model=dict)
async def print_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
):
    """Get print-friendly invoice data (any authenticated user)."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    invoice = await billing_service.get_invoice_by_id(session, invoice_id)
    if not invoice:
        raise AppException("Invoice not found", status_code=404)

    # Group items by tax rate
    tax_groups = billing_service.group_tax_by_rate(invoice.items)

    return {
        "invoice": InvoiceResponse.model_validate(invoice),
        "tax_breakdown": [
            {
                "gst_rate": rate,
                "base_amount_rupees": paise_to_rupees(data["base_amount_paise"]),
                "tax_amount_rupees": paise_to_rupees(data["tax_amount_paise"]),
                "total_rupees": paise_to_rupees(data["total_paise"]),
            }
            for rate, data in sorted(tax_groups.items())
        ],
    }


@router.get("/{invoice_id}/qr", response_class=Response)
async def get_invoice_qr(
    invoice_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    format: str = Query("png", pattern="^(png|data-uri)$"),
):
    """Get QR code for invoice (any authenticated user)."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    invoice = await billing_service.get_invoice_by_id(session, invoice_id)
    if not invoice:
        raise AppException("Invoice not found", status_code=404)

    if format == "png":
        # Return PNG file
        qr_png = qr_service.generate_qr_png(invoice.public_token)
        return Response(content=qr_png, media_type="image/png")
    else:
        # Return data URI
        qr_data_uri = qr_service.generate_qr_data_uri(invoice.public_token)
        return {"data_uri": qr_data_uri}
