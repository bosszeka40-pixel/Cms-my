"""Safe first-run installation service using the existing CMS database."""
from __future__ import annotations

import secrets

from . import installer
from .cms_core import CMSEngine, User


class InstallationError(ValueError):
    pass


def install_first_admin(
    engine: CMSEngine,
    username: str,
    password: str,
    password_confirm: str,
) -> User:
    """Create exactly one initial admin in the existing users table.

    The operation is intentionally refused after the installation marker exists
    or when an admin already exists. This keeps installer access fail-closed.
    """
    if installer.is_installed():
        raise InstallationError("CMS уже установлена.")

    errors = installer.validate_installation(username, password, password_confirm)
    if errors:
        raise InstallationError(" ".join(errors))

    email = username.strip().lower()
    if "@" not in email:
        raise InstallationError("Для администратора требуется корректный email.")

    existing = engine.get_user(email)
    if existing:
        raise InstallationError("Пользователь с таким email уже существует.")

    session = engine.SessionLocal()
    try:
        if session.query(User).filter(User.role == "admin").first():
            raise InstallationError("Администратор уже существует.")

        user = User(
            email=email,
            password_hash=engine.hash_password(password),
            kyc_status=False,
            role="admin",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def finalize_installation() -> None:
    """Write the marker only after all installation steps have succeeded."""
    installer.INSTALL_MARKER.parent.mkdir(parents=True, exist_ok=True)
    installer.INSTALL_MARKER.write_text(secrets.token_hex(32), encoding="utf-8")
