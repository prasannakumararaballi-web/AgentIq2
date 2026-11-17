"""Live Supabase Auth & PostgreSQL integration test harness.

This suite executes against a live Supabase project when credentials are provided in the environment:
- SUPABASE_URL
- SUPABASE_TEST_ACCESS_TOKEN
- SUPABASE_JWT_SECRET (or SUPABASE_JWKS_URL)

When these are not configured, tests explicitly skip with clear setup instructions.
"""

import os
import pytest
import httpx
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.security.jwt_validator import SupabaseJWTValidator, set_jwt_validator

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_TEST_ACCESS_TOKEN = os.getenv("SUPABASE_TEST_ACCESS_TOKEN")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL")

LIVE_SUPABASE_CONFIGURED = bool(
    SUPABASE_URL
    and not SUPABASE_URL.startswith("https://placeholder")
    and SUPABASE_TEST_ACCESS_TOKEN
)


@pytest.mark.skipif(
    not LIVE_SUPABASE_CONFIGURED,
    reason=(
        "Live Supabase integration tests skipped: SUPABASE_URL and SUPABASE_TEST_ACCESS_TOKEN "
        "not configured in environment. To execute: "
        "export SUPABASE_URL='https://<id>.supabase.co' "
        "export SUPABASE_TEST_ACCESS_TOKEN='<real_user_jwt>' "
        "pytest tests/test_supabase_integration.py"
    ),
)
class TestLiveSupabaseIntegration:
    """Verifies end-to-end token validation with a real Supabase Auth instance."""

    @pytest.fixture(autouse=True)
    def setup_live_validator(self):
        """Restore production SupabaseJWTValidator pointing to real JWKS / secret."""
        real_validator = SupabaseJWTValidator(
            jwt_secret=SUPABASE_JWT_SECRET,
            jwks_url=SUPABASE_JWKS_URL or f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            issuer=f"{SUPABASE_URL}/auth/v1",
            audience="authenticated",
        )
        set_jwt_validator(real_validator)

    async def test_live_token_verification(self):
        """Verify real token with live Supabase JWKS."""
        from apps.api.security.jwt_validator import get_jwt_validator
        validator = get_jwt_validator()
        claims = await validator.verify_token(SUPABASE_TEST_ACCESS_TOKEN)
        assert "sub" in claims
        assert "email" in claims

    def test_live_api_auth_me(self):
        """Verify live Supabase token against /api/v1/auth/me."""
        client = TestClient(app)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {SUPABASE_TEST_ACCESS_TOKEN}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data

