from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Tax Compliance & Audit Support Platform"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://taxplatform:taxplatform@localhost:5432/taxplatform"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://taxplatform:taxplatform@localhost:5432/taxplatform"

    # --- JWT / Security ---
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Seed / Bootstrap Super Admin ---
    SEED_SUPER_ADMIN_EMAIL: str = "admin@example.com"
    SEED_SUPER_ADMIN_PASSWORD: str = "ChangeMe123!"
    SEED_SUPER_ADMIN_FIRST_NAME: str = "Platform"
    SEED_SUPER_ADMIN_LAST_NAME: str = "Admin"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
