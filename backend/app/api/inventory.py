"""API routes for inventory management."""
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.models import UserRole
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.services.inventory_service import inventory_service
from app.utils.errors import AppException, AuthorizationError
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


# Schemas
class StockBatchCreate(BaseModel):
    product_id: int
    batch_number: str
    quantity: int
    purchase_price_paise: int
    expiry_date: Optional[datetime] = None


class StockAdjustment(BaseModel):
    product_id: int
    adjustment_quantity: int
    batch_id: Optional[int] = None
    reason: str = "Manual adjustment"


class StockBatchResponse(BaseModel):
    id: int
    product_id: int
    batch_number: str
    quantity: int
    initial_quantity: int
    purchase_price_paise: int
    expiry_date: Optional[datetime]
    is_active: bool
    created_at: datetime
    

    class Config:
        from_attributes = True


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    batch_id: Optional[int]
    movement_type: str
    quantity: int
    quantity_before: int
    quantity_after: int
    reference_type: Optional[str]
    reference_id: Optional[int]
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


async def require_role_for_inventory(
    required_roles: List[UserRole],
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Dependency to check user role for inventory endpoints."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    if user.role not in required_roles:
        raise AuthorizationError("Insufficient permissions for this operation")

    return user


@router.get("/batches", response_model=list[StockBatchResponse])
async def list_batches(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    product_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List stock batches with optional product filter."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    # This would need implementation to filter batches
    # For now, return empty list
    return []


@router.post("/batches", response_model=StockBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    batch_create: StockBatchCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_inventory([UserRole.ADMIN, UserRole.INVENTORY_MANAGER], auth, s)
    ),
):
    """Create a new stock batch (admin, inventory manager only)."""
    batch = await inventory_service.create_batch(
        session,
        product_id=batch_create.product_id,
        batch_number=batch_create.batch_number,
        quantity=batch_create.quantity,
        purchase_price_paise=batch_create.purchase_price_paise,
        expiry_date=batch_create.expiry_date,
        user_id=current_user.id,
    )

    await session.commit()
    return StockBatchResponse.model_validate(batch)


@router.post("/adjustments", status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    adjustment: StockAdjustment,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_inventory([UserRole.ADMIN, UserRole.INVENTORY_MANAGER], auth, s)
    ),
):
    """Adjust stock quantity (admin, inventory manager only)."""
    new_qty = await inventory_service.adjust_stock(
        session,
        product_id=adjustment.product_id,
        adjustment_quantity=adjustment.adjustment_quantity,
        batch_id=adjustment.batch_id,
        reason=adjustment.reason,
        user_id=current_user.id,
    )

    await session.commit()
    return {"new_quantity": new_qty}


@router.get("/movements", response_model=list[StockMovementResponse])
async def list_movements(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    product_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List stock movements."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    # This would need implementation to list movements
    # For now, return empty list
    return []


@router.get("/alerts/low-stock", response_model=list[dict])
async def get_low_stock_alerts(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    limit: int = Query(50, ge=1, le=100),
):
    """Get low stock alerts."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    products, total = await inventory_service.get_low_stock_items(session, skip=0, limit=limit)

    return [
        {
            "product_id": p.id,
            "name": p.name,
            "current_stock": 0,  # Would need to calculate
            "reorder_level": p.reorder_level,
        }
        for p in products
    ]


@router.get("/alerts/expiring-soon", response_model=list[dict])
async def get_expiring_soon_alerts(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100),
):
    """Get items expiring soon (within N days)."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    batches, total = await inventory_service.get_expiring_soon_items(session, days=days, skip=0, limit=limit)

    return [
        {
            "batch_id": b.id,
            "product_id": b.product_id,
            "batch_number": b.batch_number,
            "quantity": b.quantity,
            "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
        }
        for b in batches
    ]