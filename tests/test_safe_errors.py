from backend.security.safe_errors import safe_error_payload, safe_exception_message


def test_safe_exception_message_redacts_known_credentials():
    exc = RuntimeError("authentication failed for API_KEY=abc123 SECRET=xyz789")

    message = safe_exception_message(exc, ["abc123", "xyz789"])

    assert "abc123" not in message
    assert "xyz789" not in message
    assert "[REDACTED]" in message


def test_safe_error_payload_contains_no_secret_values():
    payload = safe_error_payload(ValueError("secret-token-42"), ["secret-token-42"])

    assert payload == {"error": "[REDACTED]"}
