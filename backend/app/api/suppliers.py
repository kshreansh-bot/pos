"""API routes for supplier management."""
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.models import UserRole
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.services.supplier_service import supplier_service
from app.utils.errors import AppException, AuthorizationError
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


# Schemas
class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    gst_number: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


async def require_role_for_suppliers(
    required_roles: List[UserRole],
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Dependency to check user role for supplier endpoints."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    if user.role not in required_roles:
        raise AuthorizationError("Insufficient permissions for this operation")

    return user


@router.get("/", response_model=list[SupplierResponse])
async def list_suppliers(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
):
    """List all suppliers with pagination and search."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    suppliers, total = await supplier_service.search_suppliers(
        session,
        query=search,
        skip=skip,
        limit=limit
    )

    return [SupplierResponse.model_validate(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
):
    """Get supplier by ID."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    supplier = await supplier_service.get_supplier(session, supplier_id)
    return SupplierResponse.model_validate(supplier)


@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_create: SupplierCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_suppliers([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Create a new supplier (admin, manager only)."""
    supplier = await supplier_service.create_supplier(
        session,
        name=supplier_create.name,
        contact_person=supplier_create.contact_person,
        phone=supplier_create.phone,
        email=supplier_create.email,
        address=supplier_create.address,
        gst_number=supplier_create.gst_number,
    )

    await session.commit()
    return SupplierResponse.model_validate(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_update: SupplierUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_suppliers([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Update supplier (admin, manager only)."""
    update_data = supplier_update.model_dump(exclude_unset=True)
    supplier = await supplier_service.update_supplier(session, supplier_id, **update_data)

    await session.commit()
    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_suppliers([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Delete supplier (admin, manager only)."""
    supplier = await supplier_service.deactivate_supplier(session, supplier_id)
    await session.commit()
    return None


@router.get("/search/items", response_model=list[SupplierResponse])
async def search_suppliers_endpoint(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Search suppliers by name, contact person, or phone."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    suppliers, total = await supplier_service.search_suppliers(
        session,
        query=q,
        skip=0,
        limit=limit
    )

    return [SupplierResponse.model_validate(s) for s in suppliers]