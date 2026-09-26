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
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"

    # --- Seed / Bootstrap Super Admin ---
    SEED_SUPER_ADMIN_EMAIL: str = "admin@example.com"
    SEED_SUPER_ADMIN_PASSWORD: str = "ChangeMe123!"
    SEED_SUPER_ADMIN_FIRST_NAME: str = "Platform"
    SEED_SUPER_ADMIN_LAST_NAME: str = "Admin"

    # --- Document Storage (Phase 2) ---
    # Local filesystem only for now; see app/storage/ for the provider
    # abstraction that will let this become S3 (or similar) later without
    # touching the document service, API, or database model.
    DOCUMENT_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_EXTENSIONS: str = "pdf,jpg,jpeg,png,xlsx,xls,csv,json,xml"

    # --- Notifications / Scheduler (Phase 7 & 8) ---
    COMPLIANCE_SWEEP_ENABLED: bool = True
    COMPLIANCE_SWEEP_INTERVAL_SECONDS: int = 3600
    NOTIFICATION_PROVIDER: str = "in_app"  # "in_app", "logging", "composite"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_document_extensions(self) -> set[str]:
        return {
            ext.strip().lower().lstrip(".")
            for ext in self.ALLOWED_DOCUMENT_EXTENSIONS.split(",")
            if ext.strip()
        }

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def model_post_init(self, __context) -> None:
        if self.is_production and self.JWT_SECRET_KEY == "change-me-to-a-long-random-secret-in-production":
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET_KEY cannot use the default development "
                "placeholder in production! Please set a strong, random secret via the JWT_SECRET_KEY environment variable."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
