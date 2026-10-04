"""API routes for customer and loyalty management."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.models import AuditLog, Customer, Invoice, UserRole
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.utils.errors import AppException, AuthorizationError, ValidationError

router = APIRouter(prefix="/api/customers", tags=["customers"])


# Pydantic Schemas
class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class LoyaltyAdjustRequest(BaseModel):
    points_delta: int  # Positive to add, negative to deduct
    reason: str


class CustomerInvoiceBrief(BaseModel):
    id: int
    invoice_number: str
    total_amount_paise: int
    payment_method: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    loyalty_points: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerDetailResponse(CustomerResponse):
    invoices: List[CustomerInvoiceBrief] = []


async def get_current_user_from_header(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Dependency to get authenticated user."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)
    return user


@router.get("/search", response_model=List[CustomerResponse])
async def search_customers(
    q: str = Query(..., min_length=1, description="Search by name or phone"),
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(get_current_user_from_header),
):
    """Search customers by phone number or name for POS lookup."""
    term = f"%{q.strip()}%"
    stmt = select(Customer).where(
        Customer.is_active == True,
        or_(
            Customer.name.ilike(term),
            Customer.phone.ilike(term)
        )
    ).order_by(Customer.name.asc()).limit(15)

    result = await session.execute(stmt)
    customers = result.scalars().all()
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get("/", response_model=dict)
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(get_current_user_from_header),
):
    """List all customers with pagination and optional search filter."""
    query = select(Customer)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
                Customer.email.ilike(term)
            )
        )

    # Count total
    count_stmt = select(func.count(Customer.id))
    if search and search.strip():
        term = f"%{search.strip()}%"
        count_stmt = count_stmt.where(
            or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
                Customer.email.ilike(term)
            )
        )
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    query = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    customers = result.scalars().all()

    return {
        "items": [CustomerResponse.model_validate(c) for c in customers],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(get_current_user_from_header),
):
    """Get customer details and their recent invoice history."""
    stmt = select(Customer).options(
        selectinload(Customer.invoices)
    ).where(Customer.id == customer_id)
    result = await session.execute(stmt)
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException("Customer not found", status_code=404)

    return CustomerDetailResponse.model_validate(customer)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_header),
):
    """Create a new customer."""
    # Check phone uniqueness if provided
    if customer_in.phone and customer_in.phone.strip():
        stmt = select(Customer).where(Customer.phone == customer_in.phone.strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise ValidationError(f"Customer with phone {customer_in.phone} already exists")

    customer = Customer(
        name=customer_in.name.strip(),
        phone=customer_in.phone.strip() if customer_in.phone else None,
        email=customer_in.email.strip() if customer_in.email else None,
        address=customer_in.address.strip() if customer_in.address else None,
        loyalty_points=0,
        is_active=True,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_header),
):
    """Update customer details."""
    stmt = select(Customer).where(Customer.id == customer_id)
    res = await session.execute(stmt)
    customer = res.scalar_one_or_none()
    if not customer:
        raise AppException("Customer not found", status_code=404)

    if customer_update.phone is not None and customer_update.phone.strip() != (customer.phone or ""):
        if customer_update.phone.strip():
            chk_stmt = select(Customer).where(
                Customer.phone == customer_update.phone.strip(),
                Customer.id != customer_id
            )
            chk_res = await session.execute(chk_stmt)
            if chk_res.scalar_one_or_none():
                raise ValidationError(f"Customer with phone {customer_update.phone} already exists")
        customer.phone = customer_update.phone.strip() if customer_update.phone.strip() else None

    if customer_update.name is not None:
        customer.name = customer_update.name.strip()
    if customer_update.email is not None:
        customer.email = customer_update.email.strip() if customer_update.email.strip() else None
    if customer_update.address is not None:
        customer.address = customer_update.address.strip() if customer_update.address.strip() else None
    if customer_update.is_active is not None:
        customer.is_active = customer_update.is_active

    await session.commit()
    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/loyalty/adjust", response_model=CustomerResponse)
async def adjust_loyalty_points(
    customer_id: int,
    req: LoyaltyAdjustRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_header),
):
    """Adjust customer loyalty points (admin/manager only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise AuthorizationError("Only managers and admins can manually adjust loyalty points")

    stmt = select(Customer).where(Customer.id == customer_id)
    res = await session.execute(stmt)
    customer = res.scalar_one_or_none()
    if not customer:
        raise AppException("Customer not found", status_code=404)

    old_points = customer.loyalty_points
    new_points = max(0, old_points + req.points_delta)
    customer.loyalty_points = new_points

    audit = AuditLog(
        user_id=current_user.id,
        action="loyalty_points_adjusted",
        entity_type="customer",
        entity_id=customer_id,
        old_values=f'{{"loyalty_points": {old_points}}}',
        new_values=f'{{"loyalty_points": {new_points}, "delta": {req.points_delta}}}',
        reason=req.reason
    )
    session.add(audit)
    await session.commit()
    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)
