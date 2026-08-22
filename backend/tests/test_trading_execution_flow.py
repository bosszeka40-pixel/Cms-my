from backend.bot import HFTBot


def test_strategy_risk_live_guard_bot_flow_blocks_live_by_default(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "1000")

    bot = HFTBot()
    result = bot.execute_trade(
        balance=1000,
        leverage=1,
        stop_loss_pct=0.02,
        notional=100,
    )

    assert result["allowed"] is False


def test_strategy_risk_live_guard_bot_flow_allows_safe_execution(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("MAX_ORDER_NOTIONAL", "1000")

    bot = HFTBot()
    result = bot.execute_trade(
        balance=1000,
        leverage=1,
        stop_loss_pct=0.02,
        notional=100,
    )

    assert result["allowed"] is True
    assert len(bot.stats) == 1
