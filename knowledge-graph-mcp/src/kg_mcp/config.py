"""MCP server configuration."""

from pydantic_settings import BaseSettings


class McpSettings(BaseSettings):
    """Settings loaded from environment variables."""

    KG_API_URL: str = "http://localhost:8000"
    KG_API_TIMEOUT: float = 120.0
    KG_CYPHER_READ_ONLY: bool = True
    MCP_TRANSPORT: str = "stdio"
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8080

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = McpSettings()
