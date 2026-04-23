"""Settings for Admin Aggregator."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Admin application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identity
    service_name: str = "admin"
    service_port: int = 8012
    service_env: str = "development"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "htqweb-auth"

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "htqweb"
    db_user: str = "htqweb"
    db_password: str = "change-me"
    
    # We do not set a single search_path here because we are an aggregator
    # Each model must explicitly declare its schema in `__table_args__`
    # However, since the microservice models use isolated `metadata` without `schema=` 
    # and rely on session-level `search_path`, we will use a multi-schema path here.
    db_schema: str = "user_svc, cms, media, messenger, email, task, hr, public"

    # Observability
    log_level: str = "INFO"

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
