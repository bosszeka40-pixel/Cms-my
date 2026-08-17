from pathlib import Path

import backend.installer as installer
from backend.cms_core import CMSEngine
from backend.install_service import InstallationError, finalize_installation, install_first_admin


def test_install_creates_first_admin_and_blocks_second(tmp_path, monkeypatch):
    db_path = tmp_path / "cms_test.db"
    marker = tmp_path / "instance" / ".installed"
    monkeypatch.setattr(installer, "INSTALL_MARKER", Path(marker))

    engine = CMSEngine(str(db_path))
    user = install_first_admin(engine, "admin@example.com", "A" * 12, "A" * 12)

    assert user.role == "admin"
    assert engine.secure_login("admin@example.com", "A" * 12).email == "admin@example.com"

    finalize_installation()
    try:
        install_first_admin(engine, "other@example.com", "B" * 12, "B" * 12)
        raise AssertionError("Second installation must be rejected")
    except InstallationError as exc:
        assert "установлена" in str(exc)
