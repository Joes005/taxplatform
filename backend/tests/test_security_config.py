import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_fails_fast_with_default_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="change-me-to-a-long-random-secret-in-production",
        )
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info.value)


def test_production_succeeds_with_strong_secret():
    cfg = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="super-secret-random-key-for-prod-environment-12345",
    )
    assert cfg.is_production is True
    assert cfg.JWT_SECRET_KEY == "super-secret-random-key-for-prod-environment-12345"


def test_development_allows_convenient_default_secret():
    cfg = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="change-me-to-a-long-random-secret-in-production",
    )
    assert cfg.is_production is False
    assert cfg.JWT_SECRET_KEY == "change-me-to-a-long-random-secret-in-production"
