from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserRead)
def update_profile(data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
