"""Worker process configuration settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Configuration for asynchronous Procrastinate worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url_sync: str = "postgresql://postgres:password@localhost:5432/postgres"
    worker_concurrency: int = 4
    worker_queues: List[str] = ["default", "analysis", "cleaning"]


worker_settings = WorkerSettings()

