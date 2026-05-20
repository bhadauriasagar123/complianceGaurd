"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserContext, get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.auth import (
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.middleware.security import issue_csrf_token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf")
async def get_csrf_token(response: Response) -> dict[str, str]:
    """Return CSRF token for SPA clients (Vercel → Render cross-origin)."""
    token = issue_csrf_token(response)
    return {"csrf_token": token}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = AuthService(db)
    try:
        user, org = await service.register(
            body.email,
            body.password,
            body.full_name,
            body.organization_name,
            ip_address=request.client.host if request.client else None,
        )
        from sqlalchemy import select

        from app.models.organization import OrganizationMember

        membership = (
            await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.organization_id == org.id,
                )
            )
        ).scalar_one()

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            role=membership.role,
            organization_id=org.id,
            created_at=user.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(db)
    try:
        access_token, refresh_token, user, membership = await service.login(
            body.email,
            body.password,
            body.mfa_code,
            body.organization_slug,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        _set_auth_cookies(response, access_token, refresh_token)
        settings = get_settings()
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    token = body.refresh_token or request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    service = AuthService(db)
    try:
        access_token, new_refresh = await service.refresh_tokens(token)
        _set_auth_cookies(response, access_token, new_refresh)
        settings = get_settings()
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[CurrentUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = AuthService(db)
    refresh_token = request.cookies.get("refresh_token")
    await service.logout(current_user.user_id, refresh_token)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: Annotated[CurrentUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MFASetupResponse:
    service = AuthService(db)
    secret, uri, qr_b64 = await service.setup_mfa(current_user.user_id)
    return MFASetupResponse(secret=secret, provisioning_uri=uri, qr_code_base64=qr_b64)


@router.post("/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_enable(
    body: MFAVerifyRequest,
    current_user: Annotated[CurrentUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = AuthService(db)
    try:
        await service.enable_mfa(current_user.user_id, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[CurrentUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    from sqlalchemy import select

    from app.models.user import User

    user = (await db.execute(select(User).where(User.id == current_user.user_id))).scalar_one()
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_verified=user.is_verified,
        mfa_enabled=user.mfa_enabled,
        role=current_user.role,
        organization_id=current_user.organization_id,
        created_at=user.created_at,
    )
