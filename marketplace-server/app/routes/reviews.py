from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service
from app.utils.rate_limit import limiter


router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=list[ReviewRead])
def list_product_reviews(product_id: int, db: Session = Depends(get_db)):
    return review_service.list_reviews(db, product_id)


@router.post("/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_review(
    request: Request,
    response: Response,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_service.create_review(db, user.id, data)
