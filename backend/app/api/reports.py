"""API routes for sales, tax, cashier performance, and audit reports."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.models import (
    AuditLog,
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Product,
    StockBatch,
    User,
    UserRole,
)
from app.schemas import UserResponse
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id
from app.utils.errors import AppException, AuthorizationError
from app.utils.money import paise_to_rupees

router = APIRouter(prefix="/api/reports", tags=["reports"])


async def require_management_role(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Ensure user is Manager or Admin."""
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)
    if user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise AuthorizationError("Access denied: Managers and Admins only")
    return user


# Schemas
class GstTaxSlabSummary(BaseModel):
    gst_rate: int
    base_amount_paise: int
    tax_amount_paise: int
    total_amount_paise: int


class PaymentMethodSummary(BaseModel):
    method: str
    count: int
    total_amount_paise: int


class SalesSummaryResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_invoices_completed: int
    total_invoices_cancelled: int
    total_invoices_returned: int
    gross_sales_paise: int
    total_discount_paise: int
    total_tax_paise: int
    net_sales_paise: int
    average_order_value_paise: int
    payment_methods: List[PaymentMethodSummary]
    tax_slabs: List[GstTaxSlabSummary]


class CashierPerformanceItem(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    invoices_count: int
    completed_count: int
    cancelled_count: int
    total_sales_paise: int
    average_ticket_paise: int


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str]
    action: str
    entity_type: str
    entity_id: int
    old_values: Optional[str]
    new_values: Optional[str]
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/sales/summary", response_model=SalesSummaryResponse)
async def get_sales_summary(
    start_date: Optional[str] = Query(None, description="ISO format date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO format date YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(require_management_role),
):
    """Generate comprehensive sales and GST breakdown report."""
    now = datetime.now()
    if start_date:
        dt_start = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        dt_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        dt_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        dt_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Invoices in date range
    stmt = select(Invoice).options(
        selectinload(Invoice.items)
    ).where(
        and_(
            Invoice.created_at >= dt_start,
            Invoice.created_at <= dt_end
        )
    )
    res = await session.execute(stmt)
    invoices = res.scalars().all()

    completed = [i for i in invoices if i.status == InvoiceStatus.COMPLETED]
    cancelled = [i for i in invoices if i.status == InvoiceStatus.CANCELLED]
    returned = [i for i in invoices if i.status == InvoiceStatus.RETURNED]

    gross_sales_paise = sum(i.subtotal_paise for i in completed)
    total_discount_paise = sum(i.total_discount_paise for i in completed)
    total_tax_paise = sum(i.total_tax_paise for i in completed)
    net_sales_paise = sum(i.total_amount_paise for i in completed)
    avg_order = int(net_sales_paise / len(completed)) if completed else 0

    # Payment method breakdown
    pm_dict: Dict[str, Dict[str, int]] = {}
    for i in completed:
        pm = i.payment_method.lower()
        if pm not in pm_dict:
            pm_dict[pm] = {"count": 0, "total": 0}
        pm_dict[pm]["count"] += 1
        pm_dict[pm]["total"] += i.total_amount_paise

    pm_summary = [
        PaymentMethodSummary(method=k, count=v["count"], total_amount_paise=v["total"])
        for k, v in pm_dict.items()
    ]

    # Tax slabs aggregation
    tax_slabs_dict: Dict[int, Dict[str, int]] = {0: {"base": 0, "tax": 0, "total": 0},
                                                5: {"base": 0, "tax": 0, "total": 0},
                                                12: {"base": 0, "tax": 0, "total": 0},
                                                18: {"base": 0, "tax": 0, "total": 0},
                                                28: {"base": 0, "tax": 0, "total": 0}}
    for inv in completed:
        for itm in inv.items:
            rate = itm.gst_rate
            if rate not in tax_slabs_dict:
                tax_slabs_dict[rate] = {"base": 0, "tax": 0, "total": 0}
            base = itm.line_total_paise - itm.tax_amount_paise
            tax_slabs_dict[rate]["base"] += base
            tax_slabs_dict[rate]["tax"] += itm.tax_amount_paise
            tax_slabs_dict[rate]["total"] += itm.line_total_paise

    tax_slabs = [
        GstTaxSlabSummary(
            gst_rate=k,
            base_amount_paise=v["base"],
            tax_amount_paise=v["tax"],
            total_amount_paise=v["total"]
        )
        for k, v in sorted(tax_slabs_dict.items())
        if v["total"] > 0 or k in (0, 5, 12, 18, 28)
    ]

    return SalesSummaryResponse(
        period_start=dt_start,
        period_end=dt_end,
        total_invoices_completed=len(completed),
        total_invoices_cancelled=len(cancelled),
        total_invoices_returned=len(returned),
        gross_sales_paise=gross_sales_paise,
        total_discount_paise=total_discount_paise,
        total_tax_paise=total_tax_paise,
        net_sales_paise=net_sales_paise,
        average_order_value_paise=avg_order,
        payment_methods=pm_summary,
        tax_slabs=tax_slabs
    )


@router.get("/cashiers", response_model=List[CashierPerformanceItem])
async def get_cashier_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(require_management_role),
):
    """Retrieve cashier performance metrics."""
    now = datetime.now()
    if start_date:
        dt_start = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        dt_start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        dt_end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        dt_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Get users
    u_stmt = select(User).where(User.role.in_([UserRole.CASHIER, UserRole.MANAGER, UserRole.ADMIN]))
    u_res = await session.execute(u_stmt)
    users = u_res.scalars().all()

    inv_stmt = select(Invoice).where(
        and_(
            Invoice.created_at >= dt_start,
            Invoice.created_at <= dt_end
        )
    )
    inv_res = await session.execute(inv_stmt)
    all_invoices = inv_res.scalars().all()

    perf_list: List[CashierPerformanceItem] = []
    for u in users:
        u_invs = [i for i in all_invoices if i.user_id == u.id]
        if not u_invs:
            continue
        comp = [i for i in u_invs if i.status == InvoiceStatus.COMPLETED]
        canc = [i for i in u_invs if i.status == InvoiceStatus.CANCELLED]
        tot_sales = sum(i.total_amount_paise for i in comp)
        avg = int(tot_sales / len(comp)) if comp else 0

        perf_list.append(CashierPerformanceItem(
            user_id=u.id,
            username=u.username,
            full_name=u.full_name,
            role=u.role.value,
            invoices_count=len(u_invs),
            completed_count=len(comp),
            cancelled_count=len(canc),
            total_sales_paise=tot_sales,
            average_ticket_paise=avg
        ))

    perf_list.sort(key=lambda x: x.total_sales_paise, reverse=True)
    return perf_list


@router.get("/audit-logs", response_model=dict)
async def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    _: UserResponse = Depends(require_management_role),
):
    """Query system audit trail."""
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    # Total count
    count_stmt = select(func.count(AuditLog.id))
    if action:
        count_stmt = count_stmt.where(AuditLog.action == action)
    if entity_type:
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    c_res = await session.execute(count_stmt)
    total = c_res.scalar() or 0

    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    res = await session.execute(query)
    logs = res.scalars().all()

    # Eager get usernames
    user_ids = list(set(log.user_id for log in logs))
    users_map = {}
    if user_ids:
        u_res = await session.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u.username for u in u_res.scalars().all()}

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": users_map.get(log.user_id, "Unknown"),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "reason": log.reason,
            "created_at": log.created_at,
        })

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }
