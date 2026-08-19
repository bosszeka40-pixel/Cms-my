"""Regression guard: the development admin bypass must be disabled in production."""
from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"


def _assignment(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
    raise AssertionError(f"{name} assignment not found")


def _source():
    return MAIN.read_text(encoding="utf-8")


def test_production_expression_disables_dev_bypass():
    tree = ast.parse(_source())
    value = _assignment(tree, "DEV_ADMIN_BYPASS_ENABLED")
    rendered = ast.unparse(value)
    assert "production" in rendered
    assert "!=" in rendered or "not" in rendered


def test_dev_bypass_endpoint_contains_runtime_guard():
    tree = ast.parse(_source())
    functions = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "dev_admin_bypass"
    ]
    assert len(functions) == 1
    function_source = ast.unparse(functions[0])
    assert "DEV_ADMIN_BYPASS_ENABLED" in function_source
    assert "404" in function_source


def test_production_does_not_enable_bypass_by_default():
    namespace = {"os": __import__("os")}
    value = _assignment(ast.parse(_source()), "DEV_ADMIN_BYPASS_ENABLED")
    code = compile(ast.Expression(value), "main.py", "eval")
    namespace["os"].environ["APP_ENV"] = "production"
    try:
        assert eval(code, namespace) is False
    finally:
        namespace["os"].environ.pop("APP_ENV", None)
