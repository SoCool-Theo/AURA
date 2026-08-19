"""Authentication application workflows within a caller-owned transaction."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from ..database.models import User
from ..database.repositories import UserRepository
from ..schemas.auth import LoginRequest, RegistrationRequest


_EMAIL_UNIQUE_CONSTRAINT = "uq_users_email"
_INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"


class DuplicateEmailError(Exception):
    """Raised when registration targets an existing canonical email."""


class InvalidCredentialsError(Exception):
    """Raised for every unusable email/password credential combination."""


class AuthService:
    """Coordinate credential workflows without managing transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = UserRepository(session)

    def register(self, request: RegistrationRequest) -> User:
        """Create one credential-bearing User from validated application input."""
        email = str(request.email)
        if self._repository.get_by_email(email) is not None:
            raise DuplicateEmailError

        password_hash = hash_password(request.password.get_secret_value())
        try:
            return self._repository.create(
                email=email,
                password_hash=password_hash,
            )
        except IntegrityError as error:
            if _constraint_name(error) == _EMAIL_UNIQUE_CONSTRAINT:
                raise DuplicateEmailError from error
            raise

    def authenticate(self, request: LoginRequest) -> User:
        """Return the credential-bearing User or raise one generic failure."""
        plaintext_password = request.password.get_secret_value()
        user = self._repository.get_by_email(str(request.email))

        if user is None or user.email is None or user.password_hash is None:
            verify_dummy_password(plaintext_password)
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)

        if not verify_password(plaintext_password, user.password_hash):
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)
        return user

    def create_access_token_for_user(self, user: User) -> str:
        """Delegate access-token issuance using the User UUID as subject."""
        return create_access_token(user.id)


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
