import os


REQUIRED_PRODUCTION_VARS = ("SECRET_KEY",)


def validate_environment() -> dict:
    """Validate critical runtime configuration before deployment."""
    production = os.getenv("APP_ENV", "development").lower() == "production"
    missing = [name for name in REQUIRED_PRODUCTION_VARS if not os.getenv(name)]
    return {
        "production": production,
        "valid": not (production and missing),
        "missing": missing if production else [],
    }


if __name__ == "__main__":
    result = validate_environment()
    if not result["valid"]:
        raise SystemExit("Missing production configuration: " + ", ".join(result["missing"]))
