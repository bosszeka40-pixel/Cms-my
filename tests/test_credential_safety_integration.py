from backend.security.credential_safety import redact_mapping


def test_exchange_config_is_safe_to_log():
    config = {
        "apiKey": "LIVE_API_KEY",
        "secret": "LIVE_API_SECRET",
        "password": "LIVE_PASSWORD",
        "enableRateLimit": True,
        "sandbox": True,
    }

    safe = redact_mapping(config)

    assert safe["apiKey"] == "[REDACTED]"
    assert safe["secret"] == "[REDACTED]"
    assert safe["password"] == "[REDACTED]"
    assert safe["enableRateLimit"] is True
    assert safe["sandbox"] is True
    assert "LIVE_API_KEY" not in repr(safe)
    assert "LIVE_API_SECRET" not in repr(safe)
    assert "LIVE_PASSWORD" not in repr(safe)
