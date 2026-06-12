import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.audit_service import record_audit_event


async def create_role(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    actor_user_id: uuid.UUID | None = None,
) -> Role:
    existing_role = await get_role_by_name(session, name)
    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role already exists",
        )

    role = Role(name=name.lower(), description=description)
    session.add(role)
    await session.flush()
    await record_audit_event(
        session,
        event_type="rbac.role.created",
        user_id=actor_user_id,
        event_metadata={"role_id": str(role.id), "role_name": role.name},
    )
    return role


async def create_permission(
    session: AsyncSession,
    *,
    name: str,
    resource: str,
    action: str,
    description: str | None,
    actor_user_id: uuid.UUID | None = None,
) -> Permission:
    existing_permission = await get_permission_by_name(session, name)
    if existing_permission is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission already exists",
        )

    permission = Permission(
        name=name.lower(),
        resource=resource.lower(),
        action=action.lower(),
        description=description,
    )
    session.add(permission)
    await session.flush()
    await record_audit_event(
        session,
        event_type="rbac.permission.created",
        user_id=actor_user_id,
        event_metadata={
            "permission_id": str(permission.id),
            "permission_name": permission.name,
            "resource": permission.resource,
            "action": permission.action,
        },
    )
    return permission


async def assign_permission_to_role(
    session: AsyncSession,
    *,
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    actor_user_id: uuid.UUID | None = None,
) -> None:
    role = await get_role_by_id(session, role_id)
    permission = await get_permission_by_id(session, permission_id)

    result = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )
    existing_assignment = result.scalar_one_or_none()
    if existing_assignment is not None:
        return

    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.flush()
    await record_audit_event(
        session,
        event_type="rbac.role_permission.assigned",
        user_id=actor_user_id,
        event_metadata={
            "role_id": str(role.id),
            "role_name": role.name,
            "permission_id": str(permission.id),
            "permission_name": permission.name,
        },
    )


async def assign_role_to_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_user_id: uuid.UUID | None = None,
) -> None:
    user = await get_user_by_id(session, user_id)
    role = await get_role_by_id(session, role_id)

    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    )
    existing_assignment = result.scalar_one_or_none()
    if existing_assignment is not None:
        return

    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()
    await record_audit_event(
        session,
        event_type="rbac.user_role.assigned",
        user_id=actor_user_id,
        event_metadata={
            "target_user_id": str(user.id),
            "role_id": str(role.id),
            "role_name": role.name,
        },
    )


async def get_user_permissions(session: AsyncSession, user: User) -> set[str]:
    result = await session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    )
    return set(result.scalars().all())


async def user_has_permission(
    session: AsyncSession,
    user: User,
    permission_name: str,
) -> bool:
    if user.is_superuser:
        return True

    permissions = await get_user_permissions(session, user)
    return permission_name.lower() in permissions


async def get_role_by_id(session: AsyncSession, role_id: uuid.UUID) -> Role:
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    return role


async def get_permission_by_id(
    session: AsyncSession,
    permission_id: uuid.UUID,
) -> Permission:
    result = await session.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalar_one_or_none()
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )
    return permission


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    result = await session.execute(select(Role).where(Role.name == name.lower()))
    return result.scalar_one_or_none()


async def get_permission_by_name(
    session: AsyncSession,
    name: str,
) -> Permission | None:
    result = await session.execute(
        select(Permission).where(Permission.name == name.lower())
    )
    return result.scalar_one_or_none()
