"""Regression checks for the trading execution security boundary.

These tests are intentionally static where the application endpoint is involved:
we want CI to fail if a future refactor removes the request-auth guard or routes
real exchange execution around the central gateway.
"""
from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Function {name!r} not found")


def _calls(function: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_connect_exchange_requires_authenticated_user():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    function = _function(tree, "connect_exchange")
    assert "_require_user" in _calls(function), (
        "/api/user/connect-exchange must require a session before accepting exchange credentials"
    )


def test_hft_simulation_requires_authenticated_user():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    function = _function(tree, "simulate_trade")
    assert "_require_user" in _calls(function), (
        "/api/bot/simulate must require a session even though it is simulation-only"
    )


def test_main_has_no_direct_ccxt_order_or_cancel_calls():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    forbidden = {"create_order", "cancel_order", "edit_order", "privatePostOrder", "privateDeleteOrder"}
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden:
                hits.append((node.lineno, node.func.attr))
    assert not hits, f"Direct exchange order API calls bypass the execution gateway: {hits}"
