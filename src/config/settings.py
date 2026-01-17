"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure OpenAI Configuration
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_name: str = "gpt-4o-realtime"
    azure_openai_api_version: str = "2024-10-01-preview"

    # Azure AI Services
    azure_ai_search_endpoint: Optional[str] = None
    azure_ai_search_key: Optional[str] = None
    azure_document_intelligence_endpoint: Optional[str] = None
    azure_document_intelligence_key: Optional[str] = None

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/inventory/vehicles.db"

    # Application Settings
    default_language: str = "fr-CA"
    quebec_compliance_mode: bool = True
    vad_threshold_dbfs: float = -45.0
    max_connections: int = 100

    # Deployment
    azure_container_registry: Optional[str] = None
    container_app_name: str = "quebec-voice-agent"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
