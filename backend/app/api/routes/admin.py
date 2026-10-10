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
    AdminAccountStatus,
    AdminDashboardResponse,
    AdminIdentityResponse,
    AdminUserRole,
    AdminUsersListResponse,
    AdminUsersQuery,
    AdminUserStatusRequest,
    AdminUserStatusResponse,
)
from app.schemas.admin_market_data import (
    AdminMarketDataQuery,
    AdminMarketInventoryResponse,
    AdminMarketObservationsResponse,
)
from app.schemas.admin_system_health import AdminSystemHealthResponse
from app.schemas.ai_monitoring import (
    AIErrorCode, AIOutcome, AIProviderKind, AIRefusalStage,
    AIMonitoringSummaryResponse, AIMonitoringTimeQuery, AIRequestsListResponse, AIRequestsQuery,
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
from app.services.admin_user_service import AdminUserService, AdminUserStatusError
from app.services.admin_system_health_service import AdminSystemHealthService
from app.services.ai_monitoring_service import AIMonitoringService
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
    status: Annotated[AdminAccountStatus | None, Query()] = None,
) -> AdminUsersListResponse:
    """Return safe directory metadata; no account or portfolio mutations."""
    query = AdminUsersQuery(
        limit=limit, offset=offset, q=q, role=role, account_type=account_type, status=status,
    )
    try:
        return AdminOverviewService(session).list_users(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin user directory unavailable") from error


@router.patch("/users/{user_id}/status", response_model=AdminUserStatusResponse)
def change_admin_user_status(
    user_id: UUID, request: AdminUserStatusRequest,
    session: DatabaseSession, current_admin: CurrentAdmin,
) -> AdminUserStatusResponse:
    """Commit status and its allowlisted audit event atomically."""
    try:
        response = AdminUserService(session).set_status(current_admin, user_id, request)
        session.commit()
        return response
    except AdminUserStatusError as error:
        session.rollback()
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        raise HTTPException(status_code=error.status_code, detail=str(error), headers=headers) from error
    except (SQLAlchemyError, ValidationError) as error:
        session.rollback()
        raise HTTPException(status_code=503, detail="Account status update unavailable") from error


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


@router.get("/system-health", response_model=AdminSystemHealthResponse)
def get_admin_system_health(
    session: DatabaseSession, current_admin: CurrentAdmin,
) -> AdminSystemHealthResponse:
    """Report observed component health, including structured probe failures."""
    try:
        return AdminSystemHealthService(session).get()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="Admin system health unavailable") from error


@router.get("/ai-monitoring", response_model=AIMonitoringSummaryResponse)
def get_ai_monitoring_summary(
    session: DatabaseSession,
    current_admin: CurrentAdmin,
    created_from: Annotated[AwareDatetime | None, Query()] = None,
    created_to: Annotated[AwareDatetime | None, Query()] = None,
) -> AIMonitoringSummaryResponse:
    """Read retained metadata counts and configuration presence, without AI calls."""
    try:
        query = AIMonitoringTimeQuery(created_from=created_from, created_to=created_to)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid AI monitoring time range") from error
    try:
        return AIMonitoringService(session).summary(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="AI monitoring summary unavailable") from error


@router.get("/ai-monitoring/requests", response_model=AIRequestsListResponse)
def list_ai_monitoring_requests(
    session: DatabaseSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    outcome: Annotated[AIOutcome | None, Query()] = None,
    provider_kind: Annotated[AIProviderKind | None, Query()] = None,
    refusal_stage: Annotated[AIRefusalStage | None, Query()] = None,
    error_code: Annotated[AIErrorCode | None, Query()] = None,
    created_from: Annotated[AwareDatetime | None, Query()] = None,
    created_to: Annotated[AwareDatetime | None, Query()] = None,
) -> AIRequestsListResponse:
    """Browse safe operational outcomes without prompts, answers, or identities."""
    try:
        query = AIRequestsQuery(
            limit=limit, offset=offset, outcome=outcome, provider_kind=provider_kind,
            refusal_stage=refusal_stage, error_code=error_code,
            created_from=created_from, created_to=created_to,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid AI monitoring filters") from error
    try:
        return AIMonitoringService(session).list(query)
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(status_code=503, detail="AI monitoring requests unavailable") from error


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
