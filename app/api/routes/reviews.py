from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DailyPlanCreate, DailyPlanOut, ReviewPayload, WeeklyReviewNotePayload
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/weekly")
def weekly_review(week_start: date, week_end: date, db: Session = Depends(get_db)):
    return ReviewService(db).generate_weekly_review(week_start, week_end)


@router.post("/weekly/note")
def save_weekly_note(payload: WeeklyReviewNotePayload, db: Session = Depends(get_db)):
    return ReviewService(db).save_weekly_review_note(
        payload.week_start, payload.week_end, payload.user_notes
    )


@router.get("/daily-plans", response_model=list[DailyPlanOut])
def list_daily_plans(
    start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)
):
    return ReviewService(db).list_daily_plans(start_date=start_date, end_date=end_date)


@router.post("/daily-plans", response_model=DailyPlanOut)
def create_daily_plan(payload: DailyPlanCreate, db: Session = Depends(get_db)):
    return ReviewService(db).create_daily_plan(payload.model_dump())


@router.post("/trades/{trade_id}/review")
def review_trade(trade_id: int, payload: ReviewPayload, db: Session = Depends(get_db)):
    review = ReviewService(db).generate_trade_review(trade_id)
    review.user_notes = payload.user_notes
    review.failure_reason = payload.failure_reason
    db.commit()
    db.refresh(review)
    return review
