from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.schemas.auth import UserMeResponse

router = APIRouter(prefix="/users", tags=["users-web"])


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
