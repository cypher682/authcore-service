import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import (
    AsyncSessionDep,
    get_current_superuser,
    require_permission,
)
from app.models.user import User
from app.schemas.audit import AuditLogPublic
from app.schemas.rbac import (
    PermissionCreate,
    PermissionPublic,
    RoleCreate,
    RolePermissionAssign,
    RolePublic,
    UserRoleAssign,
)
from app.schemas.user import UserPublic
from app.services.admin_service import (
    get_user,
    list_permissions,
    list_roles,
    list_users,
)
from app.services.audit_service import list_audit_logs
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role_to_user,
    create_permission,
    create_role,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserPublic])
async def get_users(
    session: AsyncSessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_superuser),
) -> list[UserPublic]:
    return await list_users(session, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user_detail(
    user_id: uuid.UUID,
    session: AsyncSessionDep,
    _: User = Depends(get_current_superuser),
) -> UserPublic:
    return await get_user(session, user_id)


@router.get("/roles", response_model=list[RolePublic])
async def get_roles(
    session: AsyncSessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_superuser),
) -> list[RolePublic]:
    return await list_roles(session, limit=limit, offset=offset)


@router.get("/permissions", response_model=list[PermissionPublic])
async def get_permissions(
    session: AsyncSessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_superuser),
) -> list[PermissionPublic]:
    return await list_permissions(session, limit=limit, offset=offset)


@router.get("/audit-logs", response_model=list[AuditLogPublic])
async def get_audit_logs(
    session: AsyncSessionDep,
    user_id: uuid.UUID | None = None,
    event_type: str | None = None,
    audit_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_superuser),
) -> list[AuditLogPublic]:
    return await list_audit_logs(
        session,
        user_id=user_id,
        event_type=event_type,
        status=audit_status,
        limit=limit,
    )


@router.post(
    "/roles",
    response_model=RolePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_role(
    payload: RoleCreate,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_superuser),
) -> RolePublic:
    return await create_role(
        session,
        name=payload.name,
        description=payload.description,
        actor_user_id=current_user.id,
    )


@router.post(
    "/permissions",
    response_model=PermissionPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_permission(
    payload: PermissionCreate,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_superuser),
) -> PermissionPublic:
    return await create_permission(
        session,
        name=payload.name,
        resource=payload.resource,
        action=payload.action,
        description=payload.description,
        actor_user_id=current_user.id,
    )


@router.post(
    "/roles/{role_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_permission_to_role(
    role_id: uuid.UUID,
    payload: RolePermissionAssign,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_superuser),
) -> Response:
    await assign_permission_to_role(
        session,
        role_id=role_id,
        permission_id=payload.permission_id,
        actor_user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/roles",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_role_to_user(
    payload: UserRoleAssign,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_superuser),
) -> Response:
    await assign_role_to_user(
        session,
        user_id=payload.user_id,
        role_id=payload.role_id,
        actor_user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rbac/permission-check")
async def permission_check(
    current_user: User = Depends(require_permission("admin:manage")),
) -> dict[str, str]:
    return {
        "status": "allowed",
        "user_id": str(current_user.id),
        "permission": "admin:manage",
    }
