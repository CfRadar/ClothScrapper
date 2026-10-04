from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # OpenRouter API Configuration
    OPENROUTER_API_KEY: SecretStr = Field(default=SecretStr(""))
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    APP_REFERER: str = Field(default="http://localhost:5173")
    APP_TITLE: str = Field(default="Marketplace Keyword Agent")

    # Free Model IDs (Must end in :free)
    MODEL_PLANNER: str = Field(default="")
    MODEL_ANALYST: str = Field(default="")
    MODEL_SOCIAL: str = Field(default="")
    MODEL_FALLBACKS: str = Field(default="")

    # Rate Limiting & Quotas
    LLM_RPM_LIMIT: int = Field(default=16)
    LLM_DAILY_LIMIT: int = Field(default=45)
    LLM_TIMEOUT_SECONDS: int = Field(default=90)

    # Scraper & Cache settings
    CACHE_TTL_SECONDS: int = Field(default=86400)
    MAX_QUERIES_PER_PLATFORM: int = Field(default=5)
    MAX_RESULT_PAGES: int = Field(default=2)
    MAX_PRODUCTS_PER_QUERY: int = Field(default=30)
    SCRAPE_DELAY_MIN: int = Field(default=2)
    SCRAPE_DELAY_MAX: int = Field(default=5)

    # Feature Flags & Sources
    ENABLE_X: bool = Field(default=False)
    ENABLE_INSTAGRAM: bool = Field(default=False)
    REDDIT_SUBREDDITS: str = Field(
        default="IndianFashionAddicts,IndianStreetwear,MaleFashionAdvice,femalefashionadvice,tshirts"
    )
    FRONTEND_ORIGIN: str = Field(default="http://localhost:5173")

    # SQLite Database Path
    DATABASE_PATH: str = Field(default="backend/data/app.db")

    @property
    def parsed_model_fallbacks(self) -> list[str]:
        if not self.MODEL_FALLBACKS:
            return []
        return [m.strip() for m in self.MODEL_FALLBACKS.split(",") if m.strip()]

    @property
    def parsed_reddit_subreddits(self) -> list[str]:
        if not self.REDDIT_SUBREDDITS:
            return []
        return [s.strip() for s in self.REDDIT_SUBREDDITS.split(",") if s.strip()]

    def validate_guardrails(self) -> None:
        """Validate startup guardrails: key presence and :free model suffix enforcement."""
        raw_key = self.OPENROUTER_API_KEY.get_secret_value().strip()
        if not raw_key or raw_key.startswith("sk-or-v1-xxxxxxxx"):
            raise ValueError(
                "OPENROUTER_API_KEY is not configured in backend/.env. "
                "Provide a valid key from https://openrouter.ai/keys."
            )

        models_to_check = [
            ("MODEL_PLANNER", self.MODEL_PLANNER),
            ("MODEL_ANALYST", self.MODEL_ANALYST),
            ("MODEL_SOCIAL", self.MODEL_SOCIAL),
        ] + [("MODEL_FALLBACK", m) for m in self.parsed_model_fallbacks]

        for name, model_id in models_to_check:
            if model_id and not model_id.endswith(":free"):
                raise ValueError(
                    f"Invalid model configuration: {name}='{model_id}' does not end with ':free'. "
                    f"Only OpenRouter free tier models (:free) are allowed by project guardrails."
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
