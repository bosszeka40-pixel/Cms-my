from dataclasses import dataclass


@dataclass
class LiveGuardResult:
    allowed: bool
    reason: str


def live_guard_check(risk_score: float, max_risk: float = 0.02, emergency_stop: bool = False) -> LiveGuardResult:
    """Final safety gate before a bot action is allowed."""
    if emergency_stop:
        return LiveGuardResult(False, "emergency_stop_enabled")
    if risk_score > max_risk:
        return LiveGuardResult(False, "risk_limit_exceeded")
    return LiveGuardResult(True, "approved")
