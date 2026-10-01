"""API routes for product management."""
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.models import UserRole
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.services.product_service import product_service
from app.utils.errors import AppException, AuthorizationError
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/products", tags=["products"])


# Schemas
class ProductCreate(BaseModel):
    name: str
    category_id: int
    unit: str
    mrp_paise: int
    purchase_price_paise: int
    selling_price_paise: int
    gst_rate: int
    barcode: Optional[str] = None
    brand: Optional[str] = None
    reorder_level: int = 10
    supplier_id: Optional[int] = None
    default_discount_percent: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    selling_price_paise: Optional[int] = None
    gst_rate: Optional[int] = None
    reorder_level: Optional[int] = None
    supplier_id: Optional[int] = None
    default_discount_percent: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    barcode: Optional[str]
    name: str
    brand: Optional[str]
    category_id: int
    unit: str
    mrp_paise: int
    purchase_price_paise: int
    selling_price_paise: int
    gst_rate: int
    reorder_level: int
    supplier_id: Optional[int]
    default_discount_percent: int
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


async def require_role_for_products(
    required_roles: List[UserRole],
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Dependency to check user role for product endpoints."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    if user.role not in required_roles:
        raise AuthorizationError("Insufficient permissions for this operation")

    return user


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
):
    """List all products with pagination and search."""
    token = extract_token_from_header(authorization)
    decode_token(token)  # Verify token is valid

    products, total = await product_service.search_products(
        session,
        query=search,
        category_id=category_id,
        skip=skip,
        limit=limit
    )

    return [ProductResponse.model_validate(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
):
    """Get product by ID."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    product = await product_service.get_product(session, product_id)
    return ProductResponse.model_validate(product)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_create: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_products([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Create a new product (admin, manager only)."""
    product = await product_service.create_product(
        session,
        name=product_create.name,
        category_id=product_create.category_id,
        unit=product_create.unit,
        mrp_paise=product_create.mrp_paise,
        purchase_price_paise=product_create.purchase_price_paise,
        selling_price_paise=product_create.selling_price_paise,
        gst_rate=product_create.gst_rate,
        barcode=product_create.barcode,
        brand=product_create.brand,
        reorder_level=product_create.reorder_level,
        supplier_id=product_create.supplier_id,
        default_discount_percent=product_create.default_discount_percent,
    )

    await session.commit()
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_products([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Update product (admin, manager only)."""
    update_data = product_update.model_dump(exclude_unset=True)
    product = await product_service.update_product(session, product_id, **update_data)

    await session.commit()
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(
        lambda auth=Header(None), s=Depends(get_db_session):
        require_role_for_products([UserRole.ADMIN, UserRole.MANAGER], auth, s)
    ),
):
    """Delete product (admin, manager only)."""
    product = await product_service.deactivate_product(session, product_id)
    await session.commit()
    return None


@router.get("/search/items", response_model=list[ProductResponse])
async def search_products_endpoint(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Search products by barcode, name, or brand."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    products, total = await product_service.search_products(
        session,
        query=q,
        skip=0,
        limit=limit
    )

    return [ProductResponse.model_validate(p) for p in products]


@router.get("/alerts/low-stock", response_model=list[ProductResponse])
async def get_low_stock(
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None),
    limit: int = Query(50, ge=1, le=100),
):
    """Get products below reorder level."""
    token = extract_token_from_header(authorization)
    decode_token(token)

    products, total = await product_service.get_low_stock_items(session, skip=0, limit=limit)
    return [ProductResponse.model_validate(p) for p in products]