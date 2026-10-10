"""Restricted administration entry point."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentAdmin, DatabaseSession, get_current_admin
from app.schemas.admin import (
    AdminAccountType,
    AdminDashboardResponse,
    AdminIdentityResponse,
    AdminUserRole,
    AdminUsersListResponse,
    AdminUsersQuery,
)
from app.schemas.admin_market_data import (
    AdminMarketDataQuery,
    AdminMarketInventoryResponse,
    AdminMarketObservationsResponse,
)
from app.schemas.audit_log import (
    AuditAction,
    AuditActorKind,
    AuditLogListResponse,
    AuditLogQuery,
    AuditTargetType,
)
from app.schemas.market_data_status import MarketDataStatusResponse
from app.services.admin_market_data_service import AdminMarketDataService
from app.services.admin_overview_service import AdminOverviewService
from app.services.audit_log_service import AuditLogService
from app.services.market_data_status_service import MarketDataStatusService


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/me", response_model=AdminIdentityResponse)
def get_admin_identity(current_admin: CurrentAdmin) -> AdminIdentityResponse:
    """Return a safe identity only after administrator authorization."""
    return AdminIdentityResponse(
        id=current_admin.id,
        email=current_admin.email,
        display_name=current_admin.display_name,
        role=current_admin.role,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    session: DatabaseSession, current_admin: CurrentAdmin
) -> AdminDashboardResponse:
    """Return counts of retained rows and a fixed 30-day UTC trend."""
    try:
        return AdminOverviewService(session).dashboard()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin dashboard unavailable") from error


@router.get("/users", response_model=AdminUsersListResponse)
def list_admin_users(
    session: DatabaseSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[AdminUserRole | None, Query()] = None,
    account_type: Annotated[AdminAccountType | None, Query()] = None,
) -> AdminUsersListResponse:
    """Return safe directory metadata; no account or portfolio mutations."""
    query = AdminUsersQuery(
        limit=limit, offset=offset, q=q, role=role, account_type=account_type
    )
    try:
        return AdminOverviewService(session).list_users(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin user directory unavailable") from error


@router.get("/market-data", response_model=AdminMarketInventoryResponse)
def get_admin_market_inventory(
    session: DatabaseSession, current_admin: CurrentAdmin,
) -> AdminMarketInventoryResponse:
    """Read stored counts, dates, prices, and required-instrument freshness."""
    try:
        return AdminMarketDataService(session).inventory()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin market-data inventory unavailable") from error


@router.get("/market-data/status", response_model=MarketDataStatusResponse)
def get_admin_market_status(
    session: DatabaseSession, current_admin: CurrentAdmin,
) -> MarketDataStatusResponse:
    """Reuse the shared worker status without starting a refresh or provider call."""
    try:
        return MarketDataStatusService(session).get()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin market-data status unavailable") from error


@router.get("/market-data/observations", response_model=AdminMarketObservationsResponse)
def list_admin_market_observations(
    session: DatabaseSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    symbol: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> AdminMarketObservationsResponse:
    """Browse exact stored observations, including internal FX and unexpected symbols."""
    try:
        query = AdminMarketDataQuery(
            limit=limit, offset=offset, symbol=symbol, date_from=date_from, date_to=date_to,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid market-data filters") from error
    try:
        return AdminMarketDataService(session).observations(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin market-data observations unavailable") from error


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    session: DatabaseSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    action: Annotated[AuditAction | None, Query()] = None,
    actor_kind: Annotated[AuditActorKind | None, Query()] = None,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    target_type: Annotated[AuditTargetType | None, Query()] = None,
    target_id: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[AwareDatetime | None, Query()] = None,
    created_to: Annotated[AwareDatetime | None, Query()] = None,
) -> AuditLogListResponse:
    """Read global administrative history without modifying or logging the read."""
    if (
        created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        raise HTTPException(
            status_code=422, detail="created_from must be on or before created_to"
        )
    query = AuditLogQuery(
        limit=limit,
        offset=offset,
        action=action,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=target_id,
        created_from=created_from,
        created_to=created_to,
    )
    try:
        return AuditLogService(session).list(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Audit history unavailable") from error
