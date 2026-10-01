"""Authentication registration, login, and current-user endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.database.models import User
from app.schemas.auth import (
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


router = APIRouter(prefix="/auth", tags=["Authentication"])


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


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_password(
    request: PasswordChangeRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
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
