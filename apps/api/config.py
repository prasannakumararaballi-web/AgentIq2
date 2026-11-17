"""API configuration settings loaded from environment variables."""

import json
from typing import Any, List
from pydantic import Field, field_validator
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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [i.strip() for i in v_trimmed.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["http://localhost:3000"]

    # Supabase Auth & JWT Verification
    supabase_url: str = "https://placeholder-project.supabase.co"
    supabase_jwt_secret: str = "placeholder-jwt-secret-do-not-use-in-production"
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-key"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
    direct_database_url: str = "postgresql://postgres:password@localhost:5432/postgres"
    db_echo: bool = False
    db_pool_pre_ping: bool = True

    # Storage
    local_storage_path: str = "./storage"


settings = Settings()

