from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import AsyncSessionDep, get_current_active_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    MFAChallengeResponse,
    MFAChallengeVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.mfa import MFAVerifyRequest, MFASetupResponse, MFAStatusResponse
from app.services.auth_service import (
    forgot_password,
    login_user,
    refresh_tokens,
    register_user,
    resend_verification_email,
    reset_password,
    verify_email,
    verify_mfa_challenge,
)
from app.services.mfa_service import disable_mfa, setup_mfa, verify_mfa_setup

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_auth)
async def register(
    request: Request,
    payload: RegisterRequest,
    session: AsyncSessionDep,
) -> AuthResponse:
    return await register_user(
        session,
        email=payload.email,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def verify_email_address(
    request: Request,
    payload: VerifyEmailRequest,
    session: AsyncSessionDep,
) -> MessageResponse:
    return await verify_email(
        session,
        token=payload.token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/verify-email/resend", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def resend_email_verification(
    request: Request,
    payload: ResendVerificationRequest,
    session: AsyncSessionDep,
) -> MessageResponse:
    return await resend_verification_email(
        session,
        email=payload.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/login", response_model=AuthResponse | MFAChallengeResponse)
@limiter.limit(settings.rate_limit_auth)
async def login(
    request: Request,
    payload: LoginRequest,
    session: AsyncSessionDep,
) -> AuthResponse | MFAChallengeResponse:
    return await login_user(
        session,
        email=payload.email,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/password/forgot", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def request_password_reset(
    request: Request,
    payload: ForgotPasswordRequest,
    session: AsyncSessionDep,
) -> MessageResponse:
    return await forgot_password(
        session,
        email=payload.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/password/reset", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def confirm_password_reset(
    request: Request,
    payload: ResetPasswordRequest,
    session: AsyncSessionDep,
) -> MessageResponse:
    return await reset_password(
        session,
        token=payload.token,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/mfa/challenge/verify", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def mfa_challenge_verify(
    request: Request,
    payload: MFAChallengeVerifyRequest,
    session: AsyncSessionDep,
) -> AuthResponse:
    return await verify_mfa_challenge(
        session,
        challenge_token=payload.challenge_token,
        code=payload.code,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(settings.rate_limit_auth)
async def refresh(
    request: Request,
    payload: RefreshTokenRequest,
    session: AsyncSessionDep,
) -> TokenPair:
    return await refresh_tokens(session, refresh_token=payload.refresh_token)


@router.post("/mfa/setup", response_model=MFASetupResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def mfa_setup(
    request: Request,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_active_user),
) -> MFASetupResponse:
    return await setup_mfa(session, current_user)


@router.post("/mfa/verify", response_model=MFAStatusResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def mfa_verify(
    request: Request,
    payload: MFAVerifyRequest,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_active_user),
) -> MFAStatusResponse:
    return await verify_mfa_setup(session, current_user, code=payload.code)


@router.post("/mfa/disable", response_model=MFAStatusResponse)
@limiter.limit(settings.rate_limit_sensitive)
async def mfa_disable(
    request: Request,
    payload: MFAVerifyRequest,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_active_user),
) -> MFAStatusResponse:
    return await disable_mfa(session, current_user, code=payload.code)
