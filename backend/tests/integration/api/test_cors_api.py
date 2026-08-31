import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


client = TestClient(app)
LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@pytest.mark.parametrize("origin", LOCAL_ORIGINS)
def test_local_react_origins_can_access_public_api(origin: str) -> None:
    response = client.get("/api/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", LOCAL_ORIGINS)
def test_local_react_preflight_allows_api_methods_and_headers(
    origin: str,
) -> None:
    response = client.options(
        "/api/portfolios",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    allowed_methods = {
        method.strip()
        for method in response.headers["access-control-allow-methods"].split(",")
    }
    assert allowed_methods == {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    }
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


def test_unlisted_origin_is_not_granted_cors_access() -> None:
    response = client.options(
        "/api/portfolios",
        headers={
            "Origin": "http://localhost:4173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_follow_environment_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["https://app.aura.example","https://preview.aura.example"]',
    )

    configured = Settings(_env_file=None)

    assert configured.cors_allowed_origins == (
        "https://app.aura.example",
        "https://preview.aura.example",
    )


@pytest.mark.parametrize(
    "origins",
    [
        (),
        ("*",),
        ("https://*.aura.example",),
        ("https://app.aura.example/path",),
    ],
)
def test_cors_configuration_rejects_non_explicit_origins(
    origins: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_allowed_origins=origins)
