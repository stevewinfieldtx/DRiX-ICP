"""Application settings, loaded from environment (Railway-friendly)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"

    database_url: str = "postgresql+psycopg://fitscore:fitscore@localhost:5432/fitscore"
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Tier 2 enrichment (official APIs)
    clearbit_api_key: str | None = None
    builtwith_api_key: str | None = None

    # Section 8 compliant sources (licensed APIs)
    news_api_key: str | None = None
    crunchbase_api_key: str | None = None
    people_data_api_key: str | None = None

    # Own-site polite scraper
    scraper_user_agent: str = "FitScoreBot/1.0 (+https://yourdomain.example/botinfo)"
    scraper_respect_robots: bool = True
    scraper_max_pages_per_domain: int = 8
    scraper_request_delay_seconds: float = 2.0

    # Billing
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_light: str | None = None
    stripe_price_deep: str | None = None

    @property
    def railway(self) -> bool:
        return self.environment.lower() in {"production", "railway"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
