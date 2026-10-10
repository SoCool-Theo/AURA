"""Request-scoped database and authenticated-user dependencies."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidAccessTokenError, decode_access_token_session
from app.database.connection import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.database.models import User


@lru_cache(maxsize=1)
def _get_session_factory() -> SessionFactory:
    """Create the shared factory only when a database request first needs it."""
    return create_session_factory(create_database_engine())


def get_database_session() -> Iterator[Session]:
    """Yield one caller-owned session and always close it after the request."""
    with session_scope(_get_session_factory()) as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_database_session)]


_bearer_credentials = HTTPBearer(auto_error=False)


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_credentials),
    ],
    session: DatabaseSession,
) -> User:
    """Resolve a validated Bearer token subject to its persisted User."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _authentication_error()

    try:
        user_id, auth_version = decode_access_token_session(credentials.credentials)
    except InvalidAccessTokenError as error:
        raise _authentication_error() from error

    user = session.get(User, user_id)
    if user is None or user.is_suspended or (user.auth_version or 0) != auth_version:
        raise _authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    """Authorize the persisted role, never a client field or a token role claim."""
    if (
        current_user.role != "ADMIN"
        or current_user.email is None
        or current_user.password_hash is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
