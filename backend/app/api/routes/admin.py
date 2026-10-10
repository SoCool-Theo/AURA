"""Restricted administration entry point."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentAdmin, DatabaseSession, get_current_admin
from app.schemas.admin import AdminIdentityResponse
from app.schemas.audit_log import (
    AuditAction,
    AuditActorKind,
    AuditLogListResponse,
    AuditLogQuery,
    AuditTargetType,
)
from app.services.audit_log_service import AuditLogService


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
