import uuid

import pyotp
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.services.admin_service import (
    get_user,
    list_permissions,
    list_roles,
    list_users,
)
from app.services.audit_service import list_audit_logs
from app.services.mfa_service import disable_mfa, setup_mfa, verify_mfa_setup
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role_to_user,
    create_permission,
    create_role,
    user_has_permission,
)


async def _create_user(client, email: str, password: str) -> User:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        return user


async def test_mfa_service_branches(client, unique_email, strong_password) -> None:
    user = await _create_user(client, unique_email, strong_password)

    async with AsyncSessionLocal() as session:
        setup = await setup_mfa(session, user)
        assert setup.is_enabled is False

        repeated_setup = await setup_mfa(session, user)
        assert repeated_setup.secret == setup.secret

        with pytest.raises(HTTPException) as invalid_verify:
            await verify_mfa_setup(session, user, code="000000")
        assert invalid_verify.value.status_code == 400

        code = pyotp.TOTP(setup.secret).now()
        enabled = await verify_mfa_setup(session, user, code=code)
        assert enabled.is_enabled is True

        with pytest.raises(HTTPException) as enabled_setup:
            await setup_mfa(session, user)
        assert enabled_setup.value.status_code == 409

        with pytest.raises(HTTPException) as invalid_disable:
            await disable_mfa(session, user, code="000000")
        assert invalid_disable.value.status_code == 400

        disabled = await disable_mfa(session, user, code=code)
        assert disabled.is_enabled is False


async def test_rbac_service_branches(client, unique_email, strong_password) -> None:
    user = await _create_user(client, unique_email, strong_password)
    role_name = f"role-{uuid.uuid4().hex}"
    permission_name = f"permission:{uuid.uuid4().hex}"

    async with AsyncSessionLocal() as session:
        role = await create_role(session, name=role_name, description="Test role")
        permission = await create_permission(
            session,
            name=permission_name,
            resource="test",
            action="read",
            description="Test permission",
        )

        with pytest.raises(HTTPException) as duplicate_role:
            await create_role(session, name=role_name, description=None)
        assert duplicate_role.value.status_code == 409

        with pytest.raises(HTTPException) as duplicate_permission:
            await create_permission(
                session,
                name=permission_name,
                resource="test",
                action="read",
                description=None,
            )
        assert duplicate_permission.value.status_code == 409

        await assign_permission_to_role(
            session,
            role_id=role.id,
            permission_id=permission.id,
        )
        await assign_permission_to_role(
            session,
            role_id=role.id,
            permission_id=permission.id,
        )
        await assign_role_to_user(session, user_id=user.id, role_id=role.id)
        await assign_role_to_user(session, user_id=user.id, role_id=role.id)

        assert await user_has_permission(session, user, permission_name)
        assert not await user_has_permission(session, user, "missing:permission")


async def test_admin_and_audit_query_services(
    client,
    unique_email,
    strong_password,
) -> None:
    user = await _create_user(client, unique_email, strong_password)

    async with AsyncSessionLocal() as session:
        users = await list_users(session, limit=5)
        assert any(listed_user.id == user.id for listed_user in users)

        assert (await get_user(session, user.id)).email == unique_email
        with pytest.raises(HTTPException) as missing_user:
            await get_user(session, uuid.uuid4())
        assert missing_user.value.status_code == 404

        roles = await list_roles(session, limit=5)
        permissions = await list_permissions(session, limit=5)
        assert isinstance(roles, list)
        assert isinstance(permissions, list)

        register_logs = await list_audit_logs(
            session,
            user_id=user.id,
            event_type="auth.register",
            status="success",
            limit=5,
        )
        assert any(log.event_type == "auth.register" for log in register_logs)
