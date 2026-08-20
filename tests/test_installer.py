from backend.installer import validate_installation


def test_installer_requires_strong_password():
    assert validate_installation("admin", "short", "short")


def test_installer_requires_matching_passwords():
    assert validate_installation("admin", "a" * 12, "b" * 12)


def test_installer_accepts_valid_admin():
    assert validate_installation("admin", "a" * 12, "a" * 12) == []
