"""Configuration management using pydantic-settings."""

from typing import Literal, Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Store Configuration
    store_url: HttpUrl = Field(
        ...,
        description="Shopify store URL (e.g., https://your-store.myshopify.com)",
    )
    store_password: Optional[str] = Field(
        None,
        description="Shopify store password (if protected)",
    )

    # Shopify Admin API (optional)
    shopify_admin_api_key: Optional[str] = Field(
        None,
        description="Shopify Admin API key for accessing store data (optional)",
    )

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "ollama", "openrouter"] = Field(
        "openai",
        description="LLM provider: openai, anthropic, ollama, or openrouter",
    )
    llm_api_key: Optional[str] = Field(
        None,
        description="API key for the selected LLM provider",
    )
    llm_model: str = Field(
        "gpt-4",
        description="Model name for the selected LLM provider",
    )

    # MCP Configuration
    mcp_server_url: Optional[str] = Field(
        None,
        description="URL of the Shopify Dev MCP server (for HTTP/SSE)",
    )
    mcp_command: Optional[str] = Field(
        None,
        description="Command to run the MCP server (e.g., npx)",
    )
    mcp_args: list[str] = Field(
        default_factory=list,
        description="Arguments for the MCP server command",
    )
    mcp_enabled: bool = Field(
        True,
        description="Whether to use MCP for diagnostics",
    )

    # Alerting
    alert_webhook_url: Optional[str] = Field(
        None,
        description="Webhook URL for alerts (Discord/Slack)",
    )

    # Monitoring
    check_interval_minutes: int = Field(
        30,
        description="Interval in minutes between checks",
        ge=1,
    )

    # Storage
    sqlite_db_path: str = Field(
        "./nano_sre.db",
        description="Path to SQLite database file",
    )
    report_dir: str = Field(
        "reports",
        description="Directory to save incident reports",
    )

    # Privacy & Redaction
    redact_pii: bool = Field(
        False,
        description="Enable PII redaction in logs",
    )
    screenshot_blur_enabled: bool = Field(
        False,
        description="Enable blurring of PII selectors in screenshots",
    )

    @field_validator("store_url", mode="before")
    @classmethod
    def validate_store_url(cls, v: str) -> str:
        """Ensure store URL has proper format."""
        if isinstance(v, str):
            if not v.startswith("http"):
                v = f"https://{v}"
        return v

    @property
    def store_url_str(self) -> str:
        """Return store URL as string."""
        return str(self.store_url)


def get_settings() -> Settings:
    """Factory function to get settings instance."""
    return Settings()  # type: ignore[call-arg]
