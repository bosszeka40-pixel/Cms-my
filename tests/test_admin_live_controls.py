"""Regression coverage for authenticated administrative LIVE controls."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.admin import (
    LiveTogglePayload,
    live_control_audit,
    live_controls,
    set_ai_bot_live_control,
    set_bot_live_control,
    set_global_live_control,
)
from backend.security.live_controls import LIVE_CONTROL_STATE, LiveControlState


class AdminLiveControlContractTests(unittest.TestCase):
    """Keep the API and admin UI contract explicit without contacting an exchange."""

    def test_state_defaults_to_global_kill_switch_enabled(self):
        state = LiveControlState()
        self.assertTrue(state.global_kill_switch)
        self.assertEqual(state.bot_live, {})
        self.assertEqual(state.ai_bot_live, {})

    def test_bot_and_ai_bot_toggles_are_independent_and_audited(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        state.set_ai_bot_live("ai-1", enabled=True, actor="admin")
        state.set_ai_bot_live("ai-2", enabled=False, actor="admin")

        self.assertTrue(state.bot_live["bot-1"])
        self.assertTrue(state.ai_bot_live["ai-1"])
        self.assertFalse(state.ai_bot_live["ai-2"])
        self.assertEqual(len(state.audit_log), 4)
        self.assertTrue(all(entry["actor"] == "admin" for entry in state.audit_log))

    def test_kill_switch_blocks_enabled_bot(self):
        state = LiveControlState()
        state.set_global_kill_switch(enabled=False, actor="admin")
        state.set_bot_live("bot-1", enabled=True, actor="admin")
        self.assertFalse(state.global_kill_switch)

    def test_authenticated_admin_endpoints_mutate_global_and_individual_controls(self):
        request = SimpleNamespace(
            session={"user_email": "admin@example.com"},
            headers={"X-CSRF-Token": "csrf-test"},
        )
        admin = SimpleNamespace(email="admin@example.com", role="admin")
        with patch("backend.admin.engine.get_user", return_value=admin), patch(
            "backend.admin._csrf_token", return_value="csrf-test"
        ):
            before = LIVE_CONTROL_STATE.snapshot()
            try:
                set_global_live_control(LiveTogglePayload(enabled=False), request)
                set_bot_live_control("bot-endpoint", LiveTogglePayload(enabled=True), request)
                set_ai_bot_live_control("ai-endpoint", LiveTogglePayload(enabled=True), request)
                snapshot = live_controls(request)
                self.assertFalse(snapshot["global_kill_switch"])
                self.assertTrue(snapshot["bot_live"]["bot-endpoint"])
                self.assertTrue(snapshot["ai_bot_live"]["ai-endpoint"])
                self.assertEqual(snapshot["csrf_token"], "csrf-test")
                self.assertEqual(len(live_control_audit(request)["entries"]), len(before["audit_log"]) + 3)
            finally:
                LIVE_CONTROL_STATE.global_kill_switch = before["global_kill_switch"]
                LIVE_CONTROL_STATE.bot_live = before["bot_live"]
                LIVE_CONTROL_STATE.ai_bot_live = before["ai_bot_live"]
                LIVE_CONTROL_STATE.audit_log = before["audit_log"]

    def test_live_control_endpoints_require_admin_session(self):
        request = SimpleNamespace(session={})
        with self.assertRaises(HTTPException) as exc:
            live_controls(request)
        self.assertEqual(exc.exception.status_code, 403)

    def test_live_control_posts_require_csrf_token(self):
        admin = SimpleNamespace(email="admin@example.com", role="admin")
        missing = SimpleNamespace(session={"user_email": admin.email}, headers={})
        wrong = SimpleNamespace(session={"user_email": admin.email}, headers={"X-CSRF-Token": "wrong"})
        with patch("backend.admin.engine.get_user", return_value=admin), patch(
            "backend.admin._csrf_token", return_value="expected"
        ):
            for request in (missing, wrong):
                with self.assertRaises(HTTPException) as exc:
                    set_global_live_control(LiveTogglePayload(enabled=False), request)
                self.assertEqual(exc.exception.status_code, 403)

    def test_live_controls_issues_session_csrf_token(self):
        request = SimpleNamespace(session={"user_email": "admin@example.com"}, headers={})
        admin = SimpleNamespace(email="admin@example.com", role="admin")
        with patch("backend.admin.engine.get_user", return_value=admin):
            snapshot = live_controls(request)
        self.assertTrue(snapshot["csrf_token"])
        self.assertEqual(request.session["admin_csrf_token"], snapshot["csrf_token"])

    def test_admin_template_exposes_global_bot_and_ai_bot_controls(self):
        template = (Path(__file__).resolve().parents[1] / "templates" / "admin.html").read_text(encoding="utf-8")
        for marker in (
            'id="live-controls"',
            'data-live-global="true"',
            'data-live-global="false"',
            'live-bot-controls',
            'live-ai-bot-controls',
            '/api/admin/live-controls/global',
            '/api/admin/live-controls/bots/',
            '/api/admin/live-controls/ai-bots/',
            "X-CSRF-Token",
        ):
            self.assertIn(marker, template)


if __name__ == "__main__":
    unittest.main()
