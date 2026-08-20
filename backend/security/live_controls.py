"""Fail-closed LIVE controls for individual bots and AI bots.

The control layer is intentionally independent from the global environment gate.
A real order is allowed only when the global gate, bot-level switch, and optional
AI-bot switch all explicitly permit LIVE execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class LiveControlState:
    """Runtime representation of the administrative LIVE controls.

    New bots are disabled by default. ``global_kill_switch`` is also enabled by
    default, so a freshly constructed state cannot authorize a real order.
    """

    global_kill_switch: bool = True
    bot_live: dict[str, bool] = field(default_factory=dict)
    ai_bot_live: dict[str, bool] = field(default_factory=dict)
    audit_log: list[dict[str, object]] = field(default_factory=list)

    def _record(self, actor: str, target: str, enabled: bool, kind: str) -> None:
        self.audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "target": target,
                "enabled": enabled,
                "kind": kind,
            }
        )

    def set_global_kill_switch(self, *, enabled: bool, actor: str) -> None:
        self.global_kill_switch = enabled
        self._record(actor, "global", enabled, "global_kill_switch")

    def set_bot_live(self, bot_id: str, *, enabled: bool, actor: str) -> None:
        if not bot_id.strip():
            raise ValueError("bot_id is required")
        self.bot_live[bot_id] = enabled
        self._record(actor, bot_id, enabled, "bot_live")

    def set_ai_bot_live(self, ai_bot_id: str, *, enabled: bool, actor: str) -> None:
        if not ai_bot_id.strip():
            raise ValueError("ai_bot_id is required")
        self.ai_bot_live[ai_bot_id] = enabled
        self._record(actor, ai_bot_id, enabled, "ai_bot_live")

    def allows(self, *, bot_id: str, ai_bot_id: str | None = None) -> bool:
        """Return True only when every required LIVE control is explicitly on."""
        if self.global_kill_switch:
            return False
        if not self.bot_live.get(bot_id, False):
            return False
        if ai_bot_id is not None and not self.ai_bot_live.get(ai_bot_id, False):
            return False
        return True

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-safe administrative view without exposing internals."""
        return {
            "global_kill_switch": self.global_kill_switch,
            "bot_live": dict(self.bot_live),
            "ai_bot_live": dict(self.ai_bot_live),
            "audit_log": list(self.audit_log),
        }


# Process-local control state is intentionally fail-closed on startup. A restart
# therefore cannot silently re-enable LIVE trading. Persistent storage can be
# added later, but the execution gateway must continue to require explicit state.
LIVE_CONTROL_STATE = LiveControlState()


def assert_live_controlled(
    state: LiveControlState, *, bot_id: str, ai_bot_id: str | None = None
) -> None:
    if not state.allows(bot_id=bot_id, ai_bot_id=ai_bot_id):
        raise PermissionError("LIVE trading is disabled by administrative controls")
