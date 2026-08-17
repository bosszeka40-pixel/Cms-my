import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.security.request_policy import (
    client_safe_error,
    enforce_rate_limit,
    require_user,
    require_virtual_execution,
)


def _request(session=None, headers=None):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/test",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "session": session or {},
    }
    return Request(scope)


def test_require_user_rejects_anonymous_request():
    with pytest.raises(HTTPException) as exc:
        require_user(_request())
    assert exc.value.status_code == 401


def test_require_user_returns_session_identity():
    assert require_user(_request({"user_email": "user@example.test"})) == "user@example.test"


def test_virtual_policy_rejects_explicit_live_header():
    with pytest.raises(HTTPException) as exc:
        require_virtual_execution(
            _request({"user_email": "user@example.test"}, {"X-Trading-Mode": "live"})
        )
    assert exc.value.status_code == 403


def test_virtual_policy_accepts_default_virtual_mode():
    assert require_virtual_execution(_request({"user_email": "user@example.test"})) == "user@example.test"


def test_rate_limit_rejects_after_limit():
    key = "test-rate-limit"
    enforce_rate_limit(key, limit=2, window_seconds=60)
    enforce_rate_limit(key, limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit(key, limit=2, window_seconds=60)
    assert exc.value.status_code == 429


def test_client_safe_error_does_not_require_provider_details():
    error = client_safe_error()
    assert error.status_code == 502
    assert error.detail == "Операция не выполнена."
