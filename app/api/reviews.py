from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AuthenticatedUser, require_client
from app.models import Employee, Review, ReviewStatus, Service, User
from app.schemas import (
    AdminReviewListResponse,
    EmployeeRatingOut,
    ReviewAiSummaryOut,
    ReviewAnalyticsOut,
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewModerationRequest,
    ReviewOut,
    ReviewReplyOut,
    ReviewReplyRequest,
    ReviewReportOut,
    ReviewReportRequest,
    ReviewReportStatusRequest,
    ReviewUpdateRequest,
)
from app.services.review_ai import sanitize_comment, summarize_reviews
from app.services.reviews import ReviewError, ReviewService


router = APIRouter(tags=["reviews"])


def _error(error: ReviewError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


def _service(session: Session, settings: Settings) -> ReviewService:
    return ReviewService(
        session,
        edit_window_hours=settings.review_edit_window_hours,
    )


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreateRequest,
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        review = service.create(client, payload)
        return service.public_dict(review, client, private=True)
    except ReviewError as error:
        raise _error(error) from None


@router.get("/me/reviews", response_model=ReviewListResponse)
def list_my_reviews(
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    service = _service(session, settings)
    items, total = service.list_mine(client, page=page, page_size=page_size)
    return service.page(
        [service.public_dict(item, client, private=True) for item in items],
        page,
        page_size,
        total,
    )


@router.get("/appointments/{appointment_id}/review", response_model=ReviewOut)
def get_appointment_review(
    appointment_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        review = service.get_for_appointment(appointment_id, actor)
        return service.public_dict(review, actor, private=True)
    except ReviewError as error:
        raise _error(error) from None


@router.get("/employees/{employee_id}/reviews", response_model=ReviewListResponse)
def list_employee_reviews(
    employee_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Literal["newest", "oldest", "highest_rating", "lowest_rating"] = "newest",
    rating: Annotated[int | None, Query(ge=1, le=5)] = None,
) -> dict:
    service = _service(session, settings)
    try:
        items, total = service.list_employee(
            employee_id,
            actor,
            page=page,
            page_size=page_size,
            sorting=sort,
            rating=rating,
        )
        return service.page(
            [service.public_dict(item, actor) for item in items],
            page,
            page_size,
            total,
        )
    except ReviewError as error:
        raise _error(error) from None


@router.get("/employees/{employee_id}/rating", response_model=EmployeeRatingOut)
def get_employee_rating(
    employee_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        return _service(session, settings).rating(employee_id, actor)
    except ReviewError as error:
        raise _error(error) from None


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        review = service.get_authorized(review_id, actor)
        return service.public_dict(review, actor)
    except ReviewError as error:
        raise _error(error) from None


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: UUID,
    payload: ReviewUpdateRequest,
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        review = service.update(review_id, client, payload)
        return service.public_dict(review, client, private=True)
    except ReviewError as error:
        raise _error(error) from None


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_review(
    review_id: UUID,
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    try:
        _service(session, settings).withdraw(review_id, client)
    except ReviewError as error:
        raise _error(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reviews/{review_id}/reports",
    response_model=ReviewReportOut,
    status_code=status.HTTP_201_CREATED,
)
def report_review(
    review_id: UUID,
    payload: ReviewReportRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        return _service(session, settings).report(review_id, actor, payload)
    except ReviewError as error:
        raise _error(error) from None


@router.put("/reviews/{review_id}/reply", response_model=ReviewReplyOut)
def upsert_review_reply(
    review_id: UUID,
    payload: ReviewReplyRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        reply = service.upsert_reply(review_id, actor, payload.text)
        review = service.get_authorized(review_id, actor)
        return service.public_dict(review, actor, private=True)["reply"]
    except ReviewError as error:
        raise _error(error) from None


@router.patch("/admin/reviews/{review_id}/moderation", response_model=ReviewOut)
def moderate_review(
    review_id: UUID,
    payload: ReviewModerationRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    service = _service(session, settings)
    try:
        review = service.moderate(review_id, actor, payload.status, payload.reason)
        return service.public_dict(review, actor, private=True)
    except ReviewError as error:
        raise _error(error) from None


@router.get(
    "/admin/organizations/{organization_id}/reviews",
    response_model=AdminReviewListResponse,
)
def list_admin_reviews(
    organization_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    review_status: Annotated[ReviewStatus | None, Query(alias="status")] = None,
) -> dict:
    service = _service(session, settings)
    try:
        items, total = service.list_admin(
            organization_id,
            actor,
            page=page,
            page_size=page_size,
            status=review_status,
        )
        return service.page(
            [service.admin_dict(item, actor) for item in items],
            page,
            page_size,
            total,
        )
    except ReviewError as error:
        raise _error(error) from None


@router.patch("/admin/review-reports/{report_id}", response_model=ReviewReportOut)
def resolve_review_report(
    report_id: UUID,
    payload: ReviewReportStatusRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        return _service(session, settings).resolve_report(report_id, actor, payload.status)
    except ReviewError as error:
        raise _error(error) from None


@router.get("/admin/organizations/{organization_id}/reviews/analytics", response_model=ReviewAnalyticsOut)
def review_analytics(
    organization_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: UUID | None = None,
    service_id: UUID | None = None,
    rating: Annotated[int | None, Query(ge=1, le=5)] = None,
) -> dict:
    try:
        return _service(session, settings).analytics(
            organization_id,
            actor,
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            service_id=service_id,
            rating=rating,
        )
    except ReviewError as error:
        raise _error(error) from None


@router.get(
    "/admin/organizations/{organization_id}/reviews/ai-summary",
    response_model=ReviewAiSummaryOut,
)
def review_ai_summary(
    organization_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    locale: Literal["ru", "en"] = "ru",
) -> dict:
    service = _service(session, settings)
    try:
        service.analytics(organization_id, actor)
    except ReviewError as error:
        raise _error(error) from None
    rows = session.execute(
        select(
            Review.overall_rating,
            Review.created_at,
            Review.comment,
            Employee.display_name,
            Service.name,
        )
        .join(Employee, Employee.id == Review.employee_id)
        .join(Service, Service.id == Review.service_id)
        .where(
            Review.organization_id == organization_id,
            Review.status.in_([ReviewStatus.PUBLISHED, ReviewStatus.FLAGGED]),
        )
        .order_by(Review.created_at.desc())
        .limit(200)
    )
    minimal_rows = [
        {
            "rating": row[0],
            "date": row[1].date().isoformat(),
            "comment": sanitize_comment(row[2]),
            "employee": row[3],
            "service": row[4],
        }
        for row in rows
    ]
    if not minimal_rows:
        return {
            "summary": "Недостаточно отзывов для анализа." if locale == "ru" else "Not enough reviews to analyze.",
            "generated_by": "fallback",
            "disclaimer": "AI summary is informational and must not be used as an automatic basis for sanctions.",
        }
    return {
        "summary": summarize_reviews(settings, minimal_rows, locale),
        "generated_by": "gemini",
        "disclaimer": "AI summary is informational and must not be used as an automatic basis for sanctions.",
    }
    AdminReviewListResponse,
