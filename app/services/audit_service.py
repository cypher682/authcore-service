import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    event_metadata: dict | None = None,
    status: str = "success",
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata=event_metadata,
        status=status,
    )
    session.add(audit_log)
    await session.flush()
    return audit_log


async def list_audit_logs(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    event_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[AuditLog]:
    query: Select[tuple[AuditLog]] = select(AuditLog)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if event_type is not None:
        query = query.where(AuditLog.event_type == event_type)
    if status is not None:
        query = query.where(AuditLog.status == status)

    result = await session.execute(
        query.order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
