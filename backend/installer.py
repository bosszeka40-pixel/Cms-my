"""First-run installer for Super CMS."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from werkzeug.security import generate_password_hash

INSTALL_MARKER = Path(os.getenv("CMS_INSTALL_MARKER", "instance/.installed"))


def is_installed() -> bool:
    return INSTALL_MARKER.exists()


def validate_installation(admin_username: str, admin_password: str, admin_password_confirm: str) -> list[str]:
    errors: list[str] = []
    username = admin_username.strip()
    if len(username) < 3 or len(username) > 80:
        errors.append("Имя администратора должно содержать от 3 до 80 символов.")
    if not admin_password or len(admin_password) < 12:
        errors.append("Пароль администратора должен содержать минимум 12 символов.")
    if admin_password != admin_password_confirm:
        errors.append("Пароли не совпадают.")
    return errors


def create_install_marker() -> None:
    INSTALL_MARKER.parent.mkdir(parents=True, exist_ok=True)
    INSTALL_MARKER.write_text(secrets.token_hex(32), encoding="utf-8")


def password_hash(password: str) -> str:
    return generate_password_hash(password, method="scrypt")
