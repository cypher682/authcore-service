import hashlib
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_totp,
    verify_password,
)
from app.models.mfa import MFAConfig
from app.models.token import RefreshTokenFamily
from app.models.user import User
from app.schemas.auth import AuthResponse, MFAChallengeResponse, TokenPair
from app.services.bruteforce_service import (
    check_login_lockout,
    clear_failed_login,
    record_failed_login,
)
from app.services.audit_service import record_audit_event
from app.services.session_service import create_user_session


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResponse:
    normalized_email = email.lower()
    existing_user = await _get_user_by_email(session, normalized_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    try:
        hashed_password = get_password_hash(password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    user = User(
        email=normalized_email,
        hashed_password=hashed_password,
        verification_token=secrets.token_urlsafe(32),
    )
    session.add(user)
    await session.flush()

    tokens = await _issue_token_pair(session, user)
    await create_user_session(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await record_audit_event(
        session,
        event_type="auth.register",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata={"email": normalized_email},
    )
    return AuthResponse(user=user, **tokens.model_dump())


async def login_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResponse | MFAChallengeResponse:
    try:
        await check_login_lockout(email=email, ip_address=ip_address)
    except HTTPException:
        await record_audit_event(
            session,
            event_type="auth.login.locked",
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"email": email.lower()},
            status="failure",
        )
        await session.commit()
        raise

    user = await _get_user_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        await record_failed_login(email=email, ip_address=ip_address)
        await record_audit_event(
            session,
            event_type="auth.login.failure",
            user_id=user.id if user is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"email": email.lower()},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await record_audit_event(
            session,
            event_type="auth.login.inactive",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"email": email.lower()},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    await clear_failed_login(email=email, ip_address=ip_address)
    if await _user_has_enabled_mfa(session, user):
        challenge_token = create_mfa_challenge_token(subject=user.id)
        await record_audit_event(
            session,
            event_type="mfa.challenge.issued",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"email": user.email},
        )
        await session.flush()
        return MFAChallengeResponse(challenge_token=challenge_token)

    tokens = await _issue_token_pair(session, user)
    await create_user_session(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await record_audit_event(
        session,
        event_type="auth.login.success",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata={"email": user.email},
    )
    return AuthResponse(user=user, **tokens.model_dump())


async def verify_mfa_challenge(
    session: AsyncSession,
    *,
    challenge_token: str,
    code: str,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResponse:
    try:
        payload = decode_token(challenge_token)
    except ValueError as exc:
        await record_audit_event(
            session,
            event_type="mfa.challenge.failure",
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"reason": str(exc)},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "mfa_challenge":
        await record_audit_event(
            session,
            event_type="mfa.challenge.failure",
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"reason": "invalid_token_type"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = _parse_uuid_claim(payload.get("sub"), "Invalid token subject")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        await record_audit_event(
            session,
            event_type="mfa.challenge.failure",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"reason": "invalid_user"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge",
            headers={"WWW-Authenticate": "Bearer"},
        )

    mfa_config = await _get_enabled_mfa_config(session, user)
    if mfa_config is None or not verify_totp(mfa_config.secret, code):
        await record_audit_event(
            session,
            event_type="mfa.challenge.failure",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata={"reason": "invalid_code"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    tokens = await _issue_token_pair(session, user)
    await create_user_session(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await record_audit_event(
        session,
        event_type="mfa.challenge.success",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata={"email": user.email},
    )
    return AuthResponse(user=user, **tokens.model_dump())


async def refresh_tokens(session: AsyncSession, *, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        await record_audit_event(
            session,
            event_type="auth.refresh.failure",
            event_metadata={"reason": str(exc)},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "refresh":
        await record_audit_event(
            session,
            event_type="auth.refresh.failure",
            event_metadata={"reason": "invalid_token_type"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = _parse_uuid_claim(payload.get("sub"), "Invalid token subject")
    family_id = payload.get("family_id")
    if not family_id:
        await record_audit_event(
            session,
            event_type="auth.refresh.failure",
            user_id=user_id,
            event_metadata={"reason": "missing_family_id"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token family",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        await record_audit_event(
            session,
            event_type="auth.refresh.failure",
            user_id=user_id,
            event_metadata={"reason": "invalid_user"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(
        select(RefreshTokenFamily).where(
            RefreshTokenFamily.family_id == family_id,
            RefreshTokenFamily.user_id == user.id,
        )
    )
    token_family = result.scalar_one_or_none()
    if token_family is None or token_family.is_revoked:
        await record_audit_event(
            session,
            event_type="auth.refresh.failure",
            user_id=user.id,
            event_metadata={"family_id": family_id, "reason": "invalid_family"},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token family is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented_hash = _hash_token(refresh_token)
    if token_family.last_token_hash != presented_hash:
        token_family.is_revoked = True
        await record_audit_event(
            session,
            event_type="auth.refresh.reuse_detected",
            user_id=user.id,
            event_metadata={"family_id": family_id},
            status="failure",
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id, family_id=family_id)
    token_family.last_token_hash = _hash_token(new_refresh_token)
    await record_audit_event(
        session,
        event_type="auth.refresh.success",
        user_id=user.id,
        event_metadata={"family_id": family_id},
    )
    await session.flush()

    return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)


async def _issue_token_pair(session: AsyncSession, user: User) -> TokenPair:
    family_id = str(uuid.uuid4())
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id, family_id=family_id)

    token_family = RefreshTokenFamily(
        user_id=user.id,
        family_id=family_id,
        last_token_hash=_hash_token(refresh_token),
    )
    session.add(token_family)
    await session.flush()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def _user_has_enabled_mfa(session: AsyncSession, user: User) -> bool:
    return await _get_enabled_mfa_config(session, user) is not None


async def _get_enabled_mfa_config(
    session: AsyncSession,
    user: User,
) -> MFAConfig | None:
    result = await session.execute(
        select(MFAConfig).where(
            MFAConfig.user_id == user.id,
            MFAConfig.is_enabled.is_(True),
        )
    )
    return result.scalar_one_or_none()


def _parse_uuid_claim(value: object, error_detail: str) -> uuid.UUID:
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
