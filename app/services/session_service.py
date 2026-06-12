import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.session import Session
from app.models.user import User
from app.services.audit_service import record_audit_event


async def create_user_session(
    session: AsyncSession,
    user: User,
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> Session:
    now = datetime.now(timezone.utc)
    user_session = Session(
        user_id=user.id,
        device_fingerprint=_build_device_fingerprint(
            ip_address=ip_address,
            user_agent=user_agent,
        ),
        ip_address=ip_address,
        user_agent=user_agent,
        last_active=now,
        expires_at=now + timedelta(days=settings.session_expire_days),
    )
    session.add(user_session)
    await session.flush()
    await _enforce_concurrent_session_limit(session, user)
    return user_session


async def list_user_sessions(session: AsyncSession, user: User) -> list[Session]:
    result = await session.execute(
        select(Session)
        .where(Session.user_id == user.id)
        .order_by(Session.last_active.desc())
    )
    return list(result.scalars().all())


async def delete_user_session(
    session: AsyncSession,
    user: User,
    *,
    session_id: uuid.UUID,
) -> None:
    result = await session.execute(
        delete(Session)
        .where(Session.id == session_id, Session.user_id == user.id)
        .returning(Session.id, Session.device_fingerprint)
    )
    deleted_session = result.one_or_none()
    if deleted_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await record_audit_event(
        session,
        event_type="session.revoked",
        user_id=user.id,
        event_metadata={
            "session_id": str(deleted_session.id),
            "device_fingerprint": deleted_session.device_fingerprint,
        },
    )


async def _enforce_concurrent_session_limit(
    session: AsyncSession,
    user: User,
) -> None:
    result = await session.execute(
        select(Session.id)
        .where(Session.user_id == user.id)
        .order_by(Session.last_active.desc())
        .offset(settings.max_concurrent_sessions)
    )
    expired_session_ids = list(result.scalars().all())
    if not expired_session_ids:
        return

    await session.execute(delete(Session).where(Session.id.in_(expired_session_ids)))


def _build_device_fingerprint(
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> str:
    raw_fingerprint = f"{ip_address or 'unknown'}:{user_agent or 'unknown'}"
    return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()
