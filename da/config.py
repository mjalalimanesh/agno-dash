"""
Configuration
=============

Centralized configuration for the Data Agent.

All settings can be overridden via environment variables with the
DATA_AGENT_ prefix (e.g., DATA_AGENT_MODEL=gpt-4.1).
"""

from os import getenv
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class DataAgentConfig(BaseSettings):
    """Data Agent configuration.

    Attributes:
        model: The OpenAI model to use
        max_results: Maximum knowledge base results to return
        default_limit: Default SQL LIMIT clause value
        debug: Enable debug logging
        temperature: Model temperature (0.0-1.0)
    """

    # Model settings
    model: str = Field(default="gpt-4.1", description="OpenAI model ID")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    # Knowledge base settings
    max_results: int = Field(default=10, ge=1, le=50)
    knowledge_table: str = Field(default="data_agent_knowledge")
    contents_table: str = Field(default="data_agent_contents")

    # SQL settings
    default_limit: int = Field(default=50, ge=1, le=1000)

    # Behavior
    debug: bool = Field(default=False)
    search_knowledge: bool = Field(default=True)
    enable_learning: bool = Field(default=True)
    enable_mcp: bool = Field(default=True)

    # History
    num_history_runs: int = Field(default=5, ge=0, le=20)

    class Config:
        env_prefix = "DATA_AGENT_"
        case_sensitive = False


# Singleton config instance
_config: Optional[DataAgentConfig] = None


def get_config() -> DataAgentConfig:
    """Get the Data Agent configuration.

    Returns a cached singleton instance. Configuration is loaded from
    environment variables on first access.
    """
    global _config
    if _config is None:
        _config = DataAgentConfig()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None


# Database configuration (separate for flexibility)
class DatabaseConfig(BaseSettings):
    """Database configuration."""

    driver: str = Field(default="postgresql+psycopg")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="ai")
    password: str = Field(default="ai")
    database: str = Field(default="ai")

    class Config:
        env_prefix = "DB_"
        case_sensitive = False

    @property
    def url(self) -> str:
        """Build database URL."""
        from urllib.parse import quote

        password = quote(self.password, safe="")
        return f"{self.driver}://{self.user}:{password}@{self.host}:{self.port}/{self.database}"


def get_db_config() -> DatabaseConfig:
    """Get database configuration."""
    return DatabaseConfig()


# Check for required API keys
def check_api_keys() -> dict[str, bool]:
    """Check which API keys are configured.

    Returns:
        Dict mapping key names to availability status.
    """
    return {
        "OPENAI_API_KEY": bool(getenv("OPENAI_API_KEY")),
        "EXA_API_KEY": bool(getenv("EXA_API_KEY")),
    }


def get_exa_mcp_url() -> Optional[str]:
    """Get Exa MCP URL if API key is configured."""
    api_key = getenv("EXA_API_KEY")
    if not api_key:
        return None

    return f"https://mcp.exa.ai/mcp?exaApiKey={api_key}&tools=web_search_exa,company_research_exa"
