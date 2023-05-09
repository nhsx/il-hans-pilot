import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    POSTGRES_DB: str = os.environ.get("HANS_MI_PSQL_DB", "postgres")
    POSTGRES_USER: str = os.environ.get("HANS_MI_PSQL_USER", "postgres")
    POSTGRES_PASSWORD: str = os.environ.get("HANS_MI_PSQL_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.environ.get("HANS_MI_PSQL_HOST", "db")
    POSTGRES_PORT: int = int(os.environ.get("HANS_MI_PSQL_PORT", 5432))
    SECRET_KEY: str = os.environ.get(
        "HANS_MI_SECRET_KEY",
        "django-insecure-ys038snwqt5(l_7m%p6hh8ke20+w!8fbi+@covbk)^xl1@8r%-",
    )
    APP_NAME: str = os.environ.get("APP_NAME", "management_interface")
    DEBUG: bool = bool(os.environ.get("HANS_MI_DEBUG", False))
    CSRF_TRUSTED_ORIGINS: str = os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "http://localhost"
    )
    CSV_IMPORT_MAX_LINES: int = 1000
    COGNITO_ENDPOINT: str = os.environ.get("COGNITO_ENDPOINT", "change_me")
    COGNITO_CLIENT_ID: str = os.environ.get("COGNITO_CLIENT_ID", "change_me")
    COGNITO_CLIENT_SECRET: str = os.environ.get("COGNITO_CLIENT_SECRET", "change_me")
    COGNITO_JWKS_URI: str = os.environ.get("COGNITO_JWKS_URI", "change_me")
    COGNITO_REDIRECT_URI: str = os.environ.get("COGNITO_REDIRECT_URI", "change_me")


SETTINGS = Settings()
