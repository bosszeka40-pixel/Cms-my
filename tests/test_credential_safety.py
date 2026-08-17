from backend.security.credential_safety import mask_secret, redact_mapping


def test_redact_mapping_removes_exchange_credentials():
    result = redact_mapping({
        "api_key": "KEY",
        "api_secret": "SECRET",
        "password": "PASS",
        "exchange": "binance",
    })

    assert result["api_key"] == "[REDACTED]"
    assert result["api_secret"] == "[REDACTED]"
    assert result["password"] == "[REDACTED]"
    assert result["exchange"] == "binance"


def test_mask_secret_keeps_only_small_prefix_and_suffix():
    assert mask_secret("ABCDEFGHIJKLMNOP") == "ABCD...MNOP"
    assert mask_secret("short") == "*****"
