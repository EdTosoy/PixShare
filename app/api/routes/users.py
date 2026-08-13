from app.schemas.user import UserResponse
from fastapi import APIRouter

from app.api.dependencies import CurrentUserDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUserDep):
    return current_user
