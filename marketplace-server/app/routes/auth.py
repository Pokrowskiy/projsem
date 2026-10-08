from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import TokenRead, UserLogin, UserRead, UserRegister
from app.utils.security import create_access_token, hash_password, verify_password
from app.utils.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, response: Response, data: UserRegister, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    if data.role.value == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin accounts cannot be registered")
    user = User(email=email, password_hash=hash_password(data.password), role=data.role, full_name=data.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenRead(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenRead)
@limiter.limit("10/minute")
def login(request: Request, response: Response, data: UserLogin, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return TokenRead(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserRead)
def read_current_user(user: User = Depends(get_current_user)):
    return user
