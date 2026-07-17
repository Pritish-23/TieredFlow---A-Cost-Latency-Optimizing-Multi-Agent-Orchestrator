import os

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


def _load_streamlit_secrets_into_env():
    """
    On Streamlit Community Cloud, secrets are provided via st.secrets
    (backed by a TOML file), not real environment variables.
    This copies them into os.environ so pydantic-settings can pick them up
    the same way it does locally via .env — no code branching needed elsewhere.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            for key in st.secrets.keys():
                if key not in os.environ:
                    os.environ[key] = str(st.secrets[key])
    except Exception:
        # Not running inside Streamlit, or no secrets configured — fine, .env takes over
        pass


_load_streamlit_secrets_into_env()


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
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")
    openweathermap_api_key: str = Field("", alias="OPENWEATHERMAP_API_KEY")

    # LangSmith
    langchain_tracing_v2: bool = Field(True, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field("", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field("tieredflow", alias="LANGCHAIN_PROJECT")

    # Budget
    default_budget_usd: float = Field(1.00, alias="DEFAULT_BUDGET_USD")

    # Cache
    cache_similarity_high: float = Field(0.92, alias="CACHE_SIMILARITY_HIGH")
    cache_similarity_mid: float = Field(0.75, alias="CACHE_SIMILARITY_MID")

    # Query
    query_mode: str = Field("auto", alias="QUERY_MODE")  # "auto" | "original" | "ask"


# Singleton — import this everywhere
settings = Settings()