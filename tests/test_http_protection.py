from backend.security.http_protection import RateLimiter, client_key, issue_csrf_token, verify_csrf_token


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("u", now=10)
    assert limiter.allow("u", now=11)
    assert not limiter.allow("u", now=12)
    assert limiter.allow("u", now=71)


def test_csrf_token_round_trip_and_tamper_detection():
    token = issue_csrf_token("test-secret", "session-1")
    assert verify_csrf_token("test-secret", "session-1", token)
    assert not verify_csrf_token("test-secret", "session-2", token)
    assert not verify_csrf_token("wrong-secret", "session-1", token)
    assert not verify_csrf_token("test-secret", "session-1", token + "x")


def test_client_key_prefers_authenticated_user():
    assert client_key("10.0.0.1", "user@example.com") == "user:user@example.com"
    assert client_key("10.0.0.1") == "ip:10.0.0.1"
