"""Authentication endpoints: Entra ID OIDC login, callback, logout, me."""

from __future__ import annotations

import uuid
from datetime import UTC

import msal
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.dependencies import get_db
from src.core.security import UserContext, get_current_user
from src.models.entities import GroupMapping, Tenant, User, UserRole
from src.schemas.api import UserResponse

logger = structlog.get_logger()
router = APIRouter()


def _get_msal_app() -> msal.ConfidentialClientApplication:
    """Create MSAL confidential client."""
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=settings.AZURE_AUTHORITY,
    )


@router.get("/login")
async def login(request: Request):
    """Initiate Entra ID OIDC login flow."""
    msal_app = _get_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=settings.azure_scopes_list,
        redirect_uri=settings.AZURE_REDIRECT_URI,
        state=str(uuid.uuid4()),
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle OIDC callback from Entra ID."""
    msal_app = _get_msal_app()

    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=settings.azure_scopes_list,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )

    if "error" in result:
        logger.error("MSAL token error", error=result.get("error_description"))
        raise HTTPException(status_code=401, detail=result.get("error_description", "Auth failed"))

    id_token_claims = result.get("id_token_claims", {})
    azure_tenant_id = id_token_claims.get("tid", "")
    entra_object_id = id_token_claims.get("oid", id_token_claims.get("sub", ""))
    email = id_token_claims.get("preferred_username", id_token_claims.get("email", ""))
    name = id_token_claims.get("name", email)
    groups = id_token_claims.get("groups", [])

    # Find or create tenant
    tenant = await db.scalar(select(Tenant).where(Tenant.entra_tenant_id == azure_tenant_id))
    if not tenant:
        tenant = Tenant(
            name=f"Tenant {azure_tenant_id[:8]}",
            slug=azure_tenant_id[:8].lower(),
            entra_tenant_id=azure_tenant_id,
        )
        db.add(tenant)
        await db.flush()

    # Resolve role from group mappings
    role = UserRole.viewer  # fallback
    mappings = await db.scalars(select(GroupMapping).where(GroupMapping.tenant_id == tenant.id))
    role_priority = {UserRole.admin: 3, UserRole.user: 2, UserRole.viewer: 1}
    for mapping in mappings:
        if mapping.entra_group_id in groups:
            if role_priority.get(mapping.role, 0) > role_priority.get(role, 0):
                role = mapping.role

    # Upsert user
    user = await db.scalar(
        select(User).where(User.tenant_id == tenant.id, User.entra_object_id == entra_object_id)
    )
    if user:
        user.email = email
        user.display_name = name
        user.role = role
        from datetime import datetime

        user.last_login = datetime.now(UTC)
    else:
        from datetime import datetime

        user = User(
            tenant_id=tenant.id,
            entra_object_id=entra_object_id,
            email=email,
            display_name=name,
            role=role,
            last_login=datetime.now(UTC),
        )
        db.add(user)

    await db.flush()

    # Store tokens in session/cookie — simplified for MVP
    # In production: use encrypted httpOnly cookies or server-side session
    access_token = result.get("access_token", "")

    response = RedirectResponse(url=f"{settings.API_CORS_ORIGINS.split(',')[0]}/chat")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=3600,
    )
    return response


@router.post("/logout")
async def logout():
    """Clear session and redirect."""
    response = RedirectResponse(url=f"{settings.API_CORS_ORIGINS.split(',')[0]}/login")
    response.delete_cookie("access_token")
    return response


@router.get("/me", response_model=UserResponse)
async def me(user: UserContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return current authenticated user."""
    db_user = await db.scalar(select(User).where(User.entra_object_id == user.sub))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        display_name=db_user.display_name,
        role=db_user.role.value,
        tenant_id=db_user.tenant_id,
    )
