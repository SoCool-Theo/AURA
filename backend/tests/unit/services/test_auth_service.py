from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import User
from backend.app.schemas.auth import (
    AccountDeletionRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegistrationRequest,
)
import backend.app.services.auth_service as service_module
from backend.app.services.auth_service import (
    AuthService,
    CurrentPasswordMismatchError,
    DuplicateEmailError,
    InvalidCredentialsError,
)


def _service_with_repository() -> tuple[AuthService, MagicMock, MagicMock]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=service_module.UserRepository)
    with patch.object(
        service_module,
        "UserRepository",
        return_value=repository,
    ):
        service = AuthService(session)
    return service, session, repository


def _assert_session_lifecycle_untouched(session: MagicMock) -> None:
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def _credential_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        password_hash="encoded-password-hash",
    )


def test_registration_stores_canonical_email_and_encoded_password() -> None:
    service, session, repository = _service_with_repository()
    request_data = {
        "email": "  User@Example.COM  ",
        "password": "plaintext-password",
    }
    original = deepcopy(request_data)
    request = RegistrationRequest.model_validate(request_data)
    created = _credential_user()
    repository.get_by_email.return_value = None
    repository.create.return_value = created

    with patch.object(
        service_module,
        "hash_password",
        return_value="encoded-password-hash",
    ) as hash_password:
        result = service.register(request)

    assert result is created
    repository.get_by_email.assert_called_once_with("user@example.com")
    hash_password.assert_called_once_with("plaintext-password")
    repository.create.assert_called_once_with(
        email="user@example.com",
        password_hash="encoded-password-hash",
    )
    assert request_data == original
    _assert_session_lifecycle_untouched(session)


def test_duplicate_registration_is_rejected_before_hashing() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = _credential_user()
    request = RegistrationRequest(
        email="USER@EXAMPLE.COM",
        password="plaintext-password",
    )

    with patch.object(service_module, "hash_password") as hash_password:
        with pytest.raises(DuplicateEmailError):
            service.register(request)

    repository.get_by_email.assert_called_once_with("user@example.com")
    repository.create.assert_not_called()
    hash_password.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_database_email_uniqueness_race_maps_without_service_rollback() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = None
    diagnostic = SimpleNamespace(constraint_name="uq_users_email")
    original = SimpleNamespace(diag=diagnostic)
    repository.create.side_effect = IntegrityError(
        "INSERT INTO users",
        {},
        original,
    )
    request = RegistrationRequest(
        email="user@example.com",
        password="plaintext-password",
    )

    with patch.object(
        service_module,
        "hash_password",
        return_value="encoded-password-hash",
    ):
        with pytest.raises(DuplicateEmailError) as raised:
            service.register(request)

    assert isinstance(raised.value.__cause__, IntegrityError)
    _assert_session_lifecycle_untouched(session)


def test_unrelated_integrity_error_is_propagated() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = None
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="other_constraint")
    )
    failure = IntegrityError("INSERT INTO users", {}, original)
    repository.create.side_effect = failure
    request = RegistrationRequest(
        email="user@example.com",
        password="plaintext-password",
    )

    with patch.object(
        service_module,
        "hash_password",
        return_value="encoded-password-hash",
    ):
        with pytest.raises(IntegrityError) as raised:
            service.register(request)

    assert raised.value is failure
    _assert_session_lifecycle_untouched(session)


def test_successful_authentication_returns_user_without_mutating_credentials(
) -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    original_credentials = (user.email, user.password_hash)
    repository.get_by_email.return_value = user
    request = LoginRequest(
        email="User@Example.COM",
        password="plaintext-password",
    )

    with (
        patch.object(
            service_module,
            "verify_password",
            return_value=True,
        ) as verify_password,
        patch.object(service_module, "verify_dummy_password") as verify_dummy,
    ):
        result = service.authenticate(request)

    assert result is user
    repository.get_by_email.assert_called_once_with("user@example.com")
    verify_password.assert_called_once_with(
        "plaintext-password",
        "encoded-password-hash",
    )
    verify_dummy.assert_not_called()
    assert (user.email, user.password_hash) == original_credentials
    _assert_session_lifecycle_untouched(session)


def test_wrong_password_raises_generic_invalid_credentials() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = _credential_user()
    request = LoginRequest(
        email="user@example.com",
        password="incorrect-password",
    )

    with patch.object(
        service_module,
        "verify_password",
        return_value=False,
    ):
        with pytest.raises(InvalidCredentialsError) as raised:
            service.authenticate(request)

    assert str(raised.value) == "Invalid credentials"
    _assert_session_lifecycle_untouched(session)


def test_unknown_email_uses_dummy_verification_and_same_generic_error() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = None
    request = LoginRequest(
        email="missing@example.com",
        password="unknown-password",
    )

    with patch.object(service_module, "verify_dummy_password") as verify_dummy:
        with pytest.raises(InvalidCredentialsError) as raised:
            service.authenticate(request)

    assert str(raised.value) == "Invalid credentials"
    verify_dummy.assert_called_once_with("unknown-password")
    _assert_session_lifecycle_untouched(session)


def test_credentialless_legacy_user_is_not_authenticatable() -> None:
    service, session, repository = _service_with_repository()
    repository.get_by_email.return_value = User(id=uuid4())
    request = LoginRequest(
        email="legacy@example.com",
        password="legacy-password",
    )

    with (
        patch.object(service_module, "verify_dummy_password") as verify_dummy,
        patch.object(service_module, "verify_password") as verify_password,
    ):
        with pytest.raises(InvalidCredentialsError) as raised:
            service.authenticate(request)

    assert str(raised.value) == "Invalid credentials"
    verify_dummy.assert_called_once_with("legacy-password")
    verify_password.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_token_issuance_delegates_user_uuid_to_phase3_helper() -> None:
    service, session, _ = _service_with_repository()
    user = _credential_user()

    with patch.object(
        service_module,
        "create_access_token",
        return_value="encoded-token",
    ) as create_access_token:
        result = service.create_access_token_for_user(user)

    assert result == "encoded-token"
    create_access_token.assert_called_once_with(user.id, auth_version=0)
    _assert_session_lifecycle_untouched(session)


def test_profile_update_verifies_email_change_and_passes_canonical_fields() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    repository.get_by_email.return_value = None
    repository.update_profile.return_value = user
    request = ProfileUpdateRequest(
        display_name="Aura Investor",
        email="NEW@Example.COM",
        phone_number="+66 81 234 5678",
        preferred_language="th",
        timezone="Asia/Yangon",
        current_password="current-password",
    )

    with patch.object(
        service_module,
        "verify_password",
        return_value=True,
    ) as verify_password:
        result = service.update_profile(user, request)

    assert result is user
    verify_password.assert_called_once_with(
        "current-password",
        "encoded-password-hash",
    )
    repository.get_by_email.assert_called_once_with("new@example.com")
    repository.update_profile.assert_called_once_with(
        user,
        {
            "email": "new@example.com",
            "display_name": "Aura Investor",
            "phone_number": "+66 81 234 5678",
            "preferred_language": "th",
            "timezone": "Asia/Yangon",
        },
    )
    _assert_session_lifecycle_untouched(session)


def test_profile_update_can_clear_optional_fields_without_password() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    repository.update_profile.return_value = user

    result = service.update_profile(
        user,
        ProfileUpdateRequest(display_name=None, phone_number=None),
    )

    assert result is user
    repository.update_profile.assert_called_once_with(
        user,
        {"display_name": None, "phone_number": None},
    )
    repository.get_by_email.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_profile_email_change_rejects_wrong_password_and_duplicate() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    request = ProfileUpdateRequest(
        email="new@example.com",
        current_password="wrong-password",
    )

    with patch.object(service_module, "verify_password", return_value=False):
        with pytest.raises(CurrentPasswordMismatchError):
            service.update_profile(user, request)

    repository.get_by_email.assert_not_called()
    repository.update_profile.assert_not_called()

    repository.get_by_email.return_value = User(
        id=uuid4(),
        email="new@example.com",
        password_hash="another-hash",
    )
    with patch.object(service_module, "verify_password", return_value=True):
        with pytest.raises(DuplicateEmailError):
            service.update_profile(user, request)

    repository.update_profile.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_profile_email_uniqueness_race_is_mapped() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    repository.get_by_email.return_value = None
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_users_email")
    )
    repository.update_profile.side_effect = IntegrityError(
        "UPDATE users",
        {},
        original,
    )
    request = ProfileUpdateRequest(
        email="new@example.com",
        current_password="current-password",
    )

    with patch.object(service_module, "verify_password", return_value=True):
        with pytest.raises(DuplicateEmailError):
            service.update_profile(user, request)

    _assert_session_lifecycle_untouched(session)


def test_password_change_verifies_current_and_hashes_replacement() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    request = PasswordChangeRequest(
        current_password="current-password",
        new_password="replacement-password",
    )

    with (
        patch.object(service_module, "verify_password", return_value=True),
        patch.object(
            service_module,
            "hash_password",
            return_value="replacement-hash",
        ) as hash_password,
    ):
        service.change_password(user, request)

    hash_password.assert_called_once_with("replacement-password")
    repository.update_password.assert_called_once_with(
        user,
        password_hash="replacement-hash",
    )
    _assert_session_lifecycle_untouched(session)


def test_password_change_rejects_wrong_current_password_without_hashing() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    request = PasswordChangeRequest(
        current_password="wrong-password",
        new_password="replacement-password",
    )

    with (
        patch.object(service_module, "verify_password", return_value=False),
        patch.object(service_module, "hash_password") as hash_password,
    ):
        with pytest.raises(CurrentPasswordMismatchError):
            service.change_password(user, request)

    hash_password.assert_not_called()
    repository.update_password.assert_not_called()
    _assert_session_lifecycle_untouched(session)


@pytest.mark.parametrize("password_hash", [None, "encoded-password-hash"])
def test_account_deletion_rejects_wrong_or_missing_credentials(password_hash) -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    user.password_hash = password_hash
    with patch.object(service_module, "verify_password", return_value=False):
        with pytest.raises(CurrentPasswordMismatchError):
            service.delete_account(user, AccountDeletionRequest(current_password="wrong-password"))
    repository.delete.assert_not_called()
    _assert_session_lifecycle_untouched(session)


def test_account_deletion_verifies_password_and_deletes_only_supplied_user() -> None:
    service, session, repository = _service_with_repository()
    user = _credential_user()
    with patch.object(service_module, "verify_password", return_value=True) as verify:
        service.delete_account(user, AccountDeletionRequest(current_password="current-password"))
    verify.assert_called_once_with("current-password", user.password_hash)
    repository.delete.assert_called_once_with(user)
    _assert_session_lifecycle_untouched(session)
