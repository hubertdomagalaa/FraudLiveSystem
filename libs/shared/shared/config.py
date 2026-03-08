from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "service"
    environment: str = "dev"
    log_level: str = "INFO"
    postgres_dsn: str = "postgresql://fraud:fraud@postgres:5432/fraud_platform"
    redis_url: str = "redis://redis:6379/0"
    redis_block_ms: int = 5000
    redis_read_count: int = 10
    redis_claim_idle_ms: int = 60000
    max_retry_attempts: int = 5
    auth_enabled: bool = True
    jwt_secret: str | None = None
    jwt_jwks_url: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_required_scope: str = "fraud.write"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    jwt_leeway_seconds: int = 30
    rate_limit_enabled: bool = True
    write_rate_limit_requests: int = 60
    write_rate_limit_window_seconds: int = 60
    tracing_enabled: bool = True
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
