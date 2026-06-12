from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_totp_secret, generate_totp_uri, verify_totp
from app.models.mfa import MFAConfig
from app.models.user import User
from app.schemas.mfa import MFASetupResponse, MFAStatusResponse
from app.services.audit_service import record_audit_event


async def setup_mfa(session: AsyncSession, user: User) -> MFASetupResponse:
    mfa_config = await _get_mfa_config(session, user)
    if mfa_config is not None and mfa_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled",
        )

    if mfa_config is None:
        secret = generate_totp_secret()
        mfa_config = MFAConfig(
            user_id=user.id,
            secret=secret,
            is_enabled=False,
        )
        session.add(mfa_config)
        await session.flush()
    else:
        secret = mfa_config.secret

    await record_audit_event(
        session,
        event_type="mfa.setup.started",
        user_id=user.id,
        event_metadata={"enabled": mfa_config.is_enabled},
    )
    return MFASetupResponse(
        secret=secret,
        provisioning_uri=generate_totp_uri(secret=secret, email=user.email),
        is_enabled=mfa_config.is_enabled,
    )


async def verify_mfa_setup(
    session: AsyncSession,
    user: User,
    *,
    code: str,
) -> MFAStatusResponse:
    mfa_config = await _require_mfa_config(session, user)
    if mfa_config.is_enabled:
        return MFAStatusResponse(is_enabled=True)

    if not verify_totp(mfa_config.secret, code):
        await record_audit_event(
            session,
            event_type="mfa.verify.failure",
            user_id=user.id,
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    mfa_config.is_enabled = True
    await record_audit_event(
        session,
        event_type="mfa.enabled",
        user_id=user.id,
    )
    await session.flush()
    return MFAStatusResponse(is_enabled=True)


async def disable_mfa(
    session: AsyncSession,
    user: User,
    *,
    code: str,
) -> MFAStatusResponse:
    mfa_config = await _require_mfa_config(session, user)
    if not mfa_config.is_enabled:
        return MFAStatusResponse(is_enabled=False)

    if not verify_totp(mfa_config.secret, code):
        await record_audit_event(
            session,
            event_type="mfa.disable.failure",
            user_id=user.id,
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    mfa_config.is_enabled = False
    await record_audit_event(
        session,
        event_type="mfa.disabled",
        user_id=user.id,
    )
    await session.flush()
    return MFAStatusResponse(is_enabled=False)


async def _get_mfa_config(session: AsyncSession, user: User) -> MFAConfig | None:
    result = await session.execute(
        select(MFAConfig).where(MFAConfig.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def _require_mfa_config(session: AsyncSession, user: User) -> MFAConfig:
    mfa_config = await _get_mfa_config(session, user)
    if mfa_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MFA setup has not been started",
        )

    return mfa_config
