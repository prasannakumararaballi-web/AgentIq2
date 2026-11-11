"""Pytest fixtures for AgentIQ tests."""

import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Ensure workspace paths are accessible
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "packages"))
sys.path.insert(0, str(BASE_DIR / "apps"))

from apps.api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client for FastAPI app."""
    test_client = TestClient(app)
    yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers representing an authorized admin/reviewer session."""
    return {
        "Authorization": "Bearer mock-test-token-valid-for-testing",
        "X-Workspace-ID": "00000000-0000-0000-0000-000000000001",
    }
