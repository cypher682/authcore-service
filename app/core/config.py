from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    app_secret_key: str
    app_title: str = "authcore-service"
    app_version: str = "1.0.0"
    app_debug: bool = False

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    mfa_challenge_expire_minutes: int = 5
    jwt_algorithm: str = "HS256"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    emails_from: str = "noreply@authcore.dev"

    # Sentry
    sentry_dsn: Optional[str] = None

    # HaveIBeenPwned
    hibp_api_key: Optional[str] = None

    # Rate limiting
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_sensitive: str = "5/minute"

    # Session
    max_concurrent_sessions: int = 5
    session_expire_days: int = 30

    # Lockout
    max_failed_attempts: int = 5
    lockout_ttl_seconds: int = 900

    @field_validator("app_secret_key")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if v == "change-this-to-a-long-random-secret":
            raise ValueError("APP_SECRET_KEY must be changed from the default value")
        return v


settings = Settings()
