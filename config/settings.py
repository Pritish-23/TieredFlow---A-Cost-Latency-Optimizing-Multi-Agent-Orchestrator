from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Provider keys
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")

    # LangSmith
    langchain_tracing_v2: bool = Field(True, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field("", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field("tieredflow", alias="LANGCHAIN_PROJECT")

    # Budget
    default_budget_usd: float = Field(1.00, alias="DEFAULT_BUDGET_USD")

    # Cache
    cache_similarity_high: float = Field(0.92, alias="CACHE_SIMILARITY_HIGH")
    cache_similarity_mid: float = Field(0.75, alias="CACHE_SIMILARITY_MID")


# Singleton — import this everywhere
settings = Settings()
