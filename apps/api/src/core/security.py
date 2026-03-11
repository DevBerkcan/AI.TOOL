"""Entra ID / Azure AD authentication and authorization."""

from __future__ import annotations

import time
from typing import Optional

import httpx
import structlog
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

logger = structlog.get_logger()

# ── JWKS Cache ───────────────────────────────────────────────────────────
_jwks_cache: dict = {}
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour


async def get_jwks() -> dict:
    """Fetch and cache JWKS from Entra ID."""
    global _jwks_cache, _jwks_cache_time

    if _jwks_cache and (time.time() - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    jwks_url = f"{settings.AZURE_AUTHORITY}/discovery/v2.0/keys"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = time.time()
        return _jwks_cache


# ── User Context ─────────────────────────────────────────────────────────
class UserContext(BaseModel):
    """Authenticated user extracted from JWT."""
    sub: str
    email: str
    name: str
    tenant_id: str  # Azure AD tenant
    groups: list[str] = []
    role: str = "viewer"  # resolved from group mapping


async def validate_token(request: Request) -> UserContext:
    """Validate Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth_header[7:]

    try:
        jwks = await get_jwks()

        # Decode header to find the key
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Token signing key not found")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AZURE_CLIENT_ID,
            issuer=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/v2.0",
            options={"verify_at_hash": False},
        )

        return UserContext(
            sub=payload.get("sub", ""),
            email=payload.get("preferred_username", payload.get("email", "")),
            name=payload.get("name", ""),
            tenant_id=payload.get("tid", ""),
            groups=payload.get("groups", []),
        )

    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Role helpers ─────────────────────────────────────────────────────────
def require_role(*allowed_roles: str):
    """Dependency factory: require user to have one of the allowed roles."""

    async def _check(user: UserContext = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(allowed_roles)}",
            )
        return user

    return _check


async def get_current_user(request: Request) -> UserContext:
    """Get the current authenticated user from request state (set by middleware)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
