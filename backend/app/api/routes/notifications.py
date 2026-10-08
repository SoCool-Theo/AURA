"""Authenticated in-app inbox; no push, email, or user-authored events."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.notification import NotificationListResponse, NotificationPreferencesResponse, NotificationPreferencesUpdate
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _internal_error() -> HTTPException:
    return HTTPException(status_code=500, detail="Unable to process notifications")


@router.delete("", status_code=204, response_class=Response)
def clear_all_notifications(session: DatabaseSession, current_user: CurrentUser) -> Response:
    try:
        NotificationService(session).clear_all(current_user.id)
        session.commit()
    except Exception as error:
        raise _internal_error() from error
    return Response(status_code=204)


@router.delete("/{notification_id}", status_code=204, response_class=Response)
def clear_notification(notification_id: UUID, session: DatabaseSession, current_user: CurrentUser) -> Response:
    try:
        if not NotificationService(session).clear(current_user.id, notification_id):
            raise HTTPException(status_code=404, detail="Notification not found")
        session.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise _internal_error() from error
    return Response(status_code=204)


@router.get("", response_model=NotificationListResponse)
def list_notifications(session: DatabaseSession, current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> NotificationListResponse:
    try:
        return NotificationService(session).list(current_user.id, limit=limit, offset=offset)
    except Exception as error:
        raise _internal_error() from error


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_preferences(session: DatabaseSession, current_user: CurrentUser) -> NotificationPreferencesResponse:
    try:
        return NotificationService(session).preferences(current_user.id)
    except Exception as error:
        raise _internal_error() from error


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_preferences(request: NotificationPreferencesUpdate, session: DatabaseSession, current_user: CurrentUser) -> NotificationPreferencesResponse:
    try:
        result = NotificationService(session).update_preferences(current_user.id, request)
        session.commit()
        return result
    except Exception as error:
        raise _internal_error() from error


@router.post("/read-all", status_code=204, response_class=Response)
def mark_all_read(session: DatabaseSession, current_user: CurrentUser) -> Response:
    try:
        NotificationService(session).mark_all_read(current_user.id)
        session.commit()
    except Exception as error:
        raise _internal_error() from error
    return Response(status_code=204)


@router.post("/{notification_id}/read", status_code=204, response_class=Response)
def mark_read(notification_id: UUID, session: DatabaseSession, current_user: CurrentUser) -> Response:
    try:
        found = NotificationService(session).mark_read(current_user.id, notification_id)
        if not found:
            raise HTTPException(status_code=404, detail="Notification not found")
        session.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise _internal_error() from error
    return Response(status_code=204)
