"""Authentication registration, login, and current-user endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser, DatabaseSession
from app.database.models import User
from app.core.config import settings
from app.schemas.auth import (
    AccountDeletionRequest,
    AccessTokenResponse,
    AuthenticatedUserResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegistrationRequest,
)
from app.services.auth_service import (
    AuthService,
    CurrentPasswordMismatchError,
    DuplicateEmailError,
    InvalidCredentialsError,
)
from app.services.web_session_service import (
    InvalidRefreshSessionError, RefreshConflictError, WebSessionService, WebSessionTokens,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
_REFRESH_COOKIE = "aura_refresh"


def _require_web_origin(request: Request) -> None:
    # A non-simple header plus explicit Origin validation protects cookie-backed
    # POSTs, including login/logout, independently of the SameSite deployment.
    if (
        request.headers.get("origin") not in settings.cors_allowed_origins
        or request.headers.get("x-aura-web-session") != "1"
    ):
        raise HTTPException(status_code=403, detail="Untrusted web session request")


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        _REFRESH_COOKIE, path=f"{settings.api_prefix}/auth/web",
        secure=settings.refresh_cookie_secure, httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )
    response.headers["Cache-Control"] = "no-store"


def _set_refresh_cookie(response: Response, tokens: WebSessionTokens) -> None:
    response.set_cookie(
        _REFRESH_COOKIE, tokens.refresh_token, max_age=tokens.cookie_max_age,
        path=f"{settings.api_prefix}/auth/web", secure=settings.refresh_cookie_secure,
        httponly=True, samesite=settings.refresh_cookie_samesite,
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/web/login", response_model=AccessTokenResponse)
def web_login(
    request: LoginRequest, http_request: Request, response: Response, session: DatabaseSession,
) -> AccessTokenResponse:
    _require_web_origin(http_request)
    try:
        user = AuthService(session).authenticate(request)
        tokens = WebSessionService(session).start(user, http_request.cookies.get(_REFRESH_COOKIE))
        session.commit()
    except InvalidCredentialsError as error:
        raise _invalid_login() from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to log in") from error
    _set_refresh_cookie(response, tokens)
    return AccessTokenResponse(access_token=tokens.access_token)


@router.post("/web/refresh", response_model=AccessTokenResponse)
def web_refresh(http_request: Request, response: Response, session: DatabaseSession):
    _require_web_origin(http_request)
    try:
        tokens = WebSessionService(session).refresh(http_request.cookies.get(_REFRESH_COOKIE))
        session.commit()
    except RefreshConflictError:
        # Preserve the newer shared cookie when another tab just rotated it.
        raise HTTPException(status_code=409, detail="Web session refresh is already in progress",
                            headers={"Cache-Control": "no-store"})
    except InvalidRefreshSessionError:
        try:
            session.commit()  # Persist revocation even though authentication failed.
        except Exception as error:
            raise HTTPException(status_code=500, detail="Unable to refresh web session") from error
        rejected = JSONResponse(status_code=401, content={"detail": "Web session expired or invalid"},
                                headers={"WWW-Authenticate": "Bearer"})
        _clear_refresh_cookie(rejected)
        return rejected
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to refresh web session") from error
    _set_refresh_cookie(response, tokens)
    return AccessTokenResponse(access_token=tokens.access_token)


@router.post("/web/logout", status_code=204)
def web_logout(http_request: Request, response: Response, session: DatabaseSession) -> None:
    _require_web_origin(http_request)
    expected_session_id = http_request.headers.get("x-aura-web-session-id")
    try:
        expected_session_id = UUID(expected_session_id) if expected_session_id else None
    except ValueError as error:
        raise HTTPException(status_code=403, detail="Invalid web session request") from error
    try:
        clear_cookie = WebSessionService(session).logout(
            http_request.cookies.get(_REFRESH_COOKIE), expected_session_id=expected_session_id,
        )
        session.commit()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to sign out") from error
    if clear_cookie:
        _clear_refresh_cookie(response)
    else:
        response.headers["Cache-Control"] = "no-store"


def _user_response(user: User) -> AuthenticatedUserResponse:
    if user.email is None:
        raise RuntimeError("authenticated User is missing an email")
    return AuthenticatedUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        phone_number=user.phone_number,
        preferred_language=user.preferred_language or "en",
        timezone=user.timezone or "Asia/Bangkok",
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _invalid_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/register",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegistrationRequest,
    session: DatabaseSession,
) -> AuthenticatedUserResponse:
    """Register one credential-bearing User and commit at the API boundary."""
    try:
        user = AuthService(session).register(request)
        response = _user_response(user)
        session.commit()
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register user",
        ) from error
    return response


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    request: LoginRequest,
    session: DatabaseSession,
) -> AccessTokenResponse:
    """Authenticate canonical credentials and return a Bearer access token."""
    service = AuthService(session)
    try:
        user = service.authenticate(request)
        token = service.create_access_token_for_user(user)
    except InvalidCredentialsError as error:
        raise _invalid_login() from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to log in",
        ) from error
    return AccessTokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(current_user: CurrentUser) -> AuthenticatedUserResponse:
    """Return the public representation of the authenticated User."""
    return _user_response(current_user)


def _current_password_mismatch() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Current password is incorrect",
    )


@router.patch(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
)
def update_me(
    request: ProfileUpdateRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AuthenticatedUserResponse:
    """Update the authenticated account profile and commit atomically."""
    try:
        user = AuthService(session).update_profile(current_user, request)
        response = _user_response(user)
        session.commit()
    except CurrentPasswordMismatchError as error:
        raise _current_password_mismatch() from error
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update profile",
        ) from error
    return response


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    request: AccountDeletionRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
    response: Response,
) -> None:
    """Permanently delete the authenticated account in one transaction."""
    try:
        AuthService(session).delete_account(current_user, request)
        session.commit()
    except CurrentPasswordMismatchError as error:
        raise _current_password_mismatch() from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete account",
        ) from error
    _clear_refresh_cookie(response)


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_password(
    request: PasswordChangeRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
    response: Response,
) -> None:
    """Replace the authenticated user's password and commit atomically."""
    try:
        AuthService(session).change_password(current_user, request)
        session.commit()
    except CurrentPasswordMismatchError as error:
        raise _current_password_mismatch() from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change password",
        ) from error
    _clear_refresh_cookie(response)
