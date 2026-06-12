import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role
from app.models.user import User


async def list_users(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def list_roles(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Role]:
    result = await session.execute(
        select(Role).order_by(Role.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def list_permissions(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Permission]:
    result = await session.execute(
        select(Permission)
        .order_by(Permission.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
