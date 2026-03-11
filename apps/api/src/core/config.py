"""Application configuration from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ──
    APP_NAME: str = "realcore-knowledge-ai"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    # ── API ──
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:3000"

    # ── Entra ID ──
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_AUTHORITY: str = ""
    AZURE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"
    AZURE_SCOPES: str = "openid profile email User.Read"

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://copilot:copilot@localhost:5432/copilot"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ──
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "knowledge_chunks"

    # ── Azure Storage ──
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "documents"

    # ── AI Providers ──
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-06-01"
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_CHAT_MODEL: str = "claude-sonnet-4-20250514"

    DEFAULT_CHAT_PROVIDER: str = "openai"
    DEFAULT_EMBEDDING_PROVIDER: str = "openai"

    # ── SharePoint ──
    SP_CLIENT_ID: str = ""
    SP_CLIENT_SECRET: str = ""
    SP_TENANT_ID: str = ""

    # ── Confluence ──
    CONFLUENCE_BASE_URL: str = ""
    CONFLUENCE_EMAIL: str = ""
    CONFLUENCE_API_TOKEN: str = ""

    # ── Security ──
    SESSION_SECRET: str = "change-me-to-random-64-chars"
    ENCRYPTION_KEY: str = "change-me-to-random-32-chars"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.API_CORS_ORIGINS.split(",")]

    @property
    def azure_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.AZURE_SCOPES.split(" ")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
