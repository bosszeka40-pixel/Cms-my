"""Password hashing migration without rewriting the existing database schema."""
from __future__ import annotations

import hashlib
from werkzeug.security import check_password_hash, generate_password_hash


def install_password_migration(CMSEngine) -> None:
    """Patch the existing engine class with scrypt + legacy SHA-256 migration.

    This is loaded before the application creates its main CMSEngine instance.
    Existing SHA-256 users can log in once and are transparently upgraded.
    """
    def hash_password(password: str) -> str:
        if not password:
            raise ValueError("Пароль не может быть пустым.")
        return generate_password_hash(password, method="scrypt")

    def authenticate_user(self, email: str, password: str):
        if not email or not password:
            return None
        user = self.get_user(email.strip().lower())
        if not user:
            return None

        stored = user.password_hash or ""
        if stored.startswith(("scrypt:", "pbkdf2:")):
            return user if check_password_hash(stored, password) else None

        # Legacy database compatibility: old CMS used plain SHA-256.
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if stored == legacy:
            user_id = user.id
            session = self.SessionLocal()
            try:
                migrated = session.query(type(user)).filter(type(user).id == user_id).first()
                if migrated:
                    migrated.password_hash = hash_password(password)
                    session.commit()
            finally:
                session.close()
            return user
        return None

    CMSEngine.hash_password = staticmethod(hash_password)
    CMSEngine.authenticate_user = authenticate_user
    CMSEngine.secure_login = authenticate_user
