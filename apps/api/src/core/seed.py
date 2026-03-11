"""Seed initial data for development."""

import asyncio
import uuid

from src.core.database import async_session, engine, Base
from src.models.entities import (
    Tenant, User, UserRole, GroupMapping, ModelConfig, ModelPurpose,
)


async def seed():
    """Create initial tenant, admin user, and model configs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Create default tenant
        tenant = Tenant(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Development Tenant",
            slug="dev",
            entra_tenant_id="dev-tenant-id",
            settings={"default_language": "de"},
        )
        db.add(tenant)

        # Create admin user
        admin = User(
            tenant_id=tenant.id,
            entra_object_id="dev-admin",
            email="admin@example.com",
            display_name="Admin User",
            role=UserRole.admin,
        )
        db.add(admin)

        # Create group mappings
        db.add(GroupMapping(tenant_id=tenant.id, entra_group_id="admins-group-id", role=UserRole.admin))
        db.add(GroupMapping(tenant_id=tenant.id, entra_group_id="users-group-id", role=UserRole.user))

        # Create model configs
        db.add(ModelConfig(
            tenant_id=tenant.id,
            purpose=ModelPurpose.chat,
            provider="openai",
            model_name="gpt-4o",
            is_primary=True,
        ))
        db.add(ModelConfig(
            tenant_id=tenant.id,
            purpose=ModelPurpose.chat,
            provider="claude",
            model_name="claude-sonnet-4-20250514",
            is_fallback=True,
        ))
        db.add(ModelConfig(
            tenant_id=tenant.id,
            purpose=ModelPurpose.embedding,
            provider="openai",
            model_name="text-embedding-3-small",
            is_primary=True,
        ))

        await db.commit()
        print("✅ Seed data created successfully")


if __name__ == "__main__":
    asyncio.run(seed())
