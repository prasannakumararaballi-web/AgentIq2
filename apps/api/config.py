"""API configuration settings loaded from environment variables."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "AgentIQ API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed origins for CORS requests",
    )

    # Supabase Auth
    supabase_url: str = "https://placeholder-project.supabase.co"
    supabase_jwt_secret: str = "placeholder-jwt-secret-do-not-use-in-production"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-key"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"

    # Storage
    local_storage_path: str = "./storage"


settings = Settings()

