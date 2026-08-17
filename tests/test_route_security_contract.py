from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "backend" / "main.py"


def _source() -> str:
    return MAIN.read_text(encoding="utf-8")


def _route_block(source: str, route: str, next_route: str) -> str:
    start = source.index(route)
    end = source.index(next_route, start + len(route))
    return source[start:end]


def test_exchange_connect_route_contract_requires_session_and_safe_errors():
    source = _source()
    block = _route_block(source, '@app.post("/api/user/connect-exchange")', '@app.post("/api/trading/test")')
    assert "request: Request" in block
    assert "_require_user(request)" in block
    assert "str(e)" not in block


def test_hft_simulation_route_contract_is_authenticated_and_virtual():
    source = _source()
    block = _route_block(source, '@app.post("/api/bot/simulate")', '@app.get("/api/bot/brain")')
    assert "request: Request" in block
    assert "_require_user(request)" in block or "require_virtual_execution(request)" in block
    assert "live" in block.lower()


def test_manual_trade_route_contract_is_not_presented_as_real_execution():
    source = _source()
    block = _route_block(source, '@app.post("/api/trading/manual")', '@app.get("/api/trading/history")')
    assert "_require_user(request)" in block
    assert '"status": "executed"' not in block
