import uuid

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import AsyncSessionDep, get_current_active_user
from app.models.user import User
from app.schemas.session import SessionPublic
from app.services.session_service import delete_user_session, list_user_sessions

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/sessions", response_model=list[SessionPublic])
async def get_my_sessions(
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_active_user),
) -> list[SessionPublic]:
    return await list_user_sessions(session, current_user)


@router.delete(
    "/me/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_my_session(
    session_id: uuid.UUID,
    session: AsyncSessionDep,
    current_user: User = Depends(get_current_active_user),
) -> Response:
    await delete_user_session(session, current_user, session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
