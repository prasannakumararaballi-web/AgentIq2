"""Cryptographic Supabase JWT token verification."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID
import jwt
from jwt import PyJWKClient, PyJWKClientError
from apps.api.config import settings

logger = logging.getLogger("agentiq.security.jwt")


class AuthenticationError(Exception):
    """Base exception for authentication failures."""

    def __init__(self, message: str, code: str = "UNAUTHORIZED"):
        super().__init__(message)
        self.message = message
        self.code = code


class BaseJWTValidator(ABC):
    """Abstract contract for token validation."""

    @abstractmethod
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Cryptographically verify JWT token and return decoded claims."""
        raise NotImplementedError


class SupabaseJWTValidator(BaseJWTValidator):
    """Production Supabase JWT verification supporting symmetric (HS256) and asymmetric (RS256/ES256) algorithms."""

    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        jwks_url: Optional[str] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        self.jwt_secret = jwt_secret or settings.supabase_jwt_secret
        self.jwks_url = jwks_url or settings.supabase_jwks_url
        self.issuer = issuer or settings.supabase_jwt_issuer
        self.audience = audience or settings.supabase_jwt_audience
        self._jwk_client: Optional[PyJWKClient] = None

        if self.jwks_url:
            try:
                self._jwk_client = PyJWKClient(self.jwks_url, cache_keys=True, max_cached_keys=16)
            except Exception as e:
                logger.warning(f"Failed to initialize PyJWKClient with {self.jwks_url}: {e}")

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Cryptographically verify token signature, expiration, audience, and issuer."""
        if not token or not token.strip():
            raise AuthenticationError("Missing token", code="MISSING_TOKEN")

        token_str = token.strip()

        # 1. Parse header without verifying signature to inspect algorithm
        try:
            unverified_header = jwt.get_unverified_header(token_str)
        except jwt.PyJWTError as e:
            raise AuthenticationError(f"Malformed JWT header: {e}", code="MALFORMED_TOKEN")

        alg = unverified_header.get("alg")
        if not alg:
            raise AuthenticationError("JWT missing 'alg' in header", code="INVALID_HEADER")

        # Configure verification options
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": bool(self.audience),
            "verify_iss": bool(self.issuer),
        }

        # 2. Select verification key based on algorithm
        try:
            if alg == "HS256":
                # Symmetric verification with Supabase JWT Secret
                if not self.jwt_secret:
                    raise AuthenticationError("Server misconfigured: missing SUPABASE_JWT_SECRET for HS256 verification")
                
                payload = jwt.decode(
                    token_str,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    audience=self.audience if self.audience else None,
                    issuer=self.issuer if self.issuer else None,
                    options=options,
                )
            elif alg in ("RS256", "ES256"):
                # Asymmetric verification with JWKS
                if not self._jwk_client:
                    raise AuthenticationError(
                        f"Server misconfigured: asymmetric algorithm '{alg}' requires configured SUPABASE_JWKS_URL"
                    )
                try:
                    signing_key = self._jwk_client.get_signing_key_from_jwt(token_str)
                    key = signing_key.key
                except PyJWKClientError as err:
                    raise AuthenticationError(f"Unable to find matching public key in JWKS: {err}", code="INVALID_KEY")

                payload = jwt.decode(
                    token_str,
                    key,
                    algorithms=[alg],
                    audience=self.audience if self.audience else None,
                    issuer=self.issuer if self.issuer else None,
                    options=options,
                )
            else:
                raise AuthenticationError(f"Unsupported signing algorithm: '{alg}'", code="UNSUPPORTED_ALGORITHM")

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Authentication token has expired. Please log in again.", code="EXPIRED_TOKEN")
        except jwt.InvalidSignatureError:
            raise AuthenticationError("Token cryptographic signature verification failed.", code="INVALID_SIGNATURE")
        except jwt.InvalidAudienceError:
            raise AuthenticationError("Token audience mismatch.", code="INVALID_AUDIENCE")
        except jwt.InvalidIssuerError:
            raise AuthenticationError("Token issuer mismatch.", code="INVALID_ISSUER")
        except jwt.PyJWTError as err:
            raise AuthenticationError(f"Invalid authentication token: {err}", code="INVALID_TOKEN")

        # 3. Validate claims format
        sub = payload.get("sub")
        if not sub:
            raise AuthenticationError("Token payload missing required 'sub' (user ID) claim.", code="MISSING_SUB")

        try:
            UUID(str(sub))
        except ValueError:
            raise AuthenticationError("Token 'sub' claim is not a valid UUID.", code="INVALID_SUB")

        return payload


# Singleton validator instance
_jwt_validator: BaseJWTValidator = SupabaseJWTValidator()


def get_jwt_validator() -> BaseJWTValidator:
    """Dependency / accessor for active JWT validator."""
    return _jwt_validator


def set_jwt_validator(validator: BaseJWTValidator) -> None:
    """Override validator for unit tests."""
    global _jwt_validator
    _jwt_validator = validator

