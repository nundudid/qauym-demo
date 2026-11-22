from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    git_sha: str = "dev"
    database_url: str = "postgresql+psycopg://qauym:qauym@localhost:5432/qauym"
    valkey_url: str = "redis://localhost:6379/0"

    session_cookie_name: str = "qauym_session"
    session_days: int = 14
    # Login and register attempts allowed per IP per minute (SPEC Section 9, rule 6).
    auth_rate_limit_per_minute: int = 10

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
