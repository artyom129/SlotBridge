from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Employee,
    OrganizationMembership,
    Review,
    ReviewAuditAction,
    ReviewAuditLog,
    ReviewReply,
    ReviewReport,
    ReviewReportStatus,
    ReviewStatus,
    Service,
    Organization,
    User,
    UserRole,
)


class ReviewError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ReviewService:
    def __init__(self, session: Session, *, edit_window_hours: int = 24):
        self.session = session
        self.edit_window = timedelta(hours=edit_window_hours)

    def _actor_org_ids(self, actor: User) -> set[UUID]:
        membership_ids = set(
            self.session.scalars(
                select(OrganizationMembership.organization_id).where(
                    OrganizationMembership.user_id == actor.id
                )
            )
        )
        employee_ids = set(
            self.session.scalars(
                select(Employee.organization_id).where(Employee.user_id == actor.id)
            )
        )
        return membership_ids | employee_ids

    def _assert_tenant(self, actor: User, organization_id: UUID) -> None:
        if organization_id not in self._actor_org_ids(actor):
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)

    def _get(self, review_id: UUID) -> Review:
        review = self.session.scalar(
            select(Review)
            .options(
                selectinload(Review.client),
                selectinload(Review.service),
                selectinload(Review.reply).selectinload(ReviewReply.author),
            )
            .where(Review.id == review_id)
        )
        if review is None:
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        return review

    def _is_admin(self, actor: User, organization_id: UUID) -> bool:
        return actor.role == UserRole.ADMIN and organization_id in self._actor_org_ids(actor)

    def _can_edit(self, review: Review, actor: User, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return (
            review.client_user_id == actor.id
            and review.status != ReviewStatus.HIDDEN
            and current <= _utc(review.created_at) + self.edit_window
        )

    def _audit(
        self,
        review: Review,
        actor: User,
        action: ReviewAuditAction,
        reason: str | None = None,
    ) -> None:
        self.session.add(
            ReviewAuditLog(
                review_id=review.id,
                organization_id=review.organization_id,
                action=action,
                actor_user_id=actor.id,
                reason=reason,
            )
        )

    def create(self, actor: User, payload) -> Review:
        from app.models import Appointment, AppointmentStatus

        appointment = self.session.get(Appointment, payload.appointment_id)
        if appointment is None or appointment.client_user_id != actor.id:
            raise ReviewError("APPOINTMENT_NOT_FOUND", "Appointment not found", 404)
        self._assert_tenant(actor, appointment.organization_id)
        if appointment.status != AppointmentStatus.COMPLETED:
            raise ReviewError(
                "APPOINTMENT_NOT_COMPLETED",
                "A review can be submitted only after the appointment is completed",
                409,
            )
        if self.session.scalar(
            select(Review.id).where(Review.appointment_id == appointment.id)
        ):
            raise ReviewError(
                "REVIEW_ALREADY_EXISTS",
                "A review already exists for this appointment",
                409,
            )
        review = Review(
            organization_id=appointment.organization_id,
            appointment_id=appointment.id,
            client_user_id=actor.id,
            employee_id=appointment.employee_id,
            service_id=appointment.service_id,
            overall_rating=payload.overall_rating,
            quality_rating=payload.quality_rating,
            service_rating=payload.service_rating,
            punctuality_rating=payload.punctuality_rating,
            comment=payload.comment,
            is_anonymous=payload.is_anonymous,
            status=ReviewStatus.PUBLISHED,
        )
        self.session.add(review)
        try:
            self.session.flush()
            self._audit(review, actor, ReviewAuditAction.REVIEW_CREATED)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ReviewError(
                "REVIEW_ALREADY_EXISTS",
                "A review already exists for this appointment",
                409,
            ) from None
        return self._get(review.id)

    def get_authorized(self, review_id: UUID, actor: User) -> Review:
        review = self._get(review_id)
        self._assert_tenant(actor, review.organization_id)
        if review.status == ReviewStatus.PUBLISHED:
            return review
        if review.client_user_id == actor.id or self._is_admin(actor, review.organization_id):
            return review
        raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)

    def get_for_appointment(self, appointment_id: UUID, actor: User) -> Review:
        from app.models import Appointment

        appointment = self.session.get(Appointment, appointment_id)
        if appointment is None:
            raise ReviewError("APPOINTMENT_NOT_FOUND", "Appointment not found", 404)
        self._assert_tenant(actor, appointment.organization_id)
        is_authorized = (
            appointment.client_user_id == actor.id
            or self._is_admin(actor, appointment.organization_id)
            or actor.role == UserRole.EMPLOYEE
            and self.session.scalar(
                select(Employee.id).where(
                    Employee.id == appointment.employee_id,
                    Employee.user_id == actor.id,
                )
            )
            is not None
        )
        if not is_authorized:
            raise ReviewError("APPOINTMENT_NOT_FOUND", "Appointment not found", 404)
        review = self.session.scalar(
            select(Review).where(Review.appointment_id == appointment_id)
        )
        if review is None:
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        return self.get_authorized(review.id, actor)

    def update(self, review_id: UUID, actor: User, payload) -> Review:
        review = self._get(review_id)
        self._assert_tenant(actor, review.organization_id)
        if review.client_user_id != actor.id:
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        if not self._can_edit(review, actor):
            raise ReviewError(
                "REVIEW_EDIT_WINDOW_EXPIRED",
                "The review edit window has expired",
                409,
            )
        for field in payload.model_fields_set:
            setattr(review, field, getattr(payload, field))
        self._audit(review, actor, ReviewAuditAction.REVIEW_UPDATED)
        self.session.commit()
        return self._get(review.id)

    def withdraw(self, review_id: UUID, actor: User) -> None:
        review = self._get(review_id)
        self._assert_tenant(actor, review.organization_id)
        if review.client_user_id != actor.id:
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        if not self._can_edit(review, actor):
            raise ReviewError(
                "REVIEW_EDIT_WINDOW_EXPIRED",
                "The review edit window has expired",
                409,
            )
        review.status = ReviewStatus.HIDDEN
        review.moderation_note = "Withdrawn by author"
        self._audit(
            review,
            actor,
            ReviewAuditAction.REVIEW_HIDDEN,
            "Withdrawn by author",
        )
        self.session.commit()

    def list_employee(
        self,
        employee_id: UUID,
        actor: User,
        *,
        page: int,
        page_size: int,
        sorting: str,
        rating: int | None = None,
    ) -> tuple[list[Review], int]:
        employee = self.session.get(Employee, employee_id)
        if employee is None:
            raise ReviewError("EMPLOYEE_NOT_FOUND", "Employee not found", 404)
        self._assert_tenant(actor, employee.organization_id)
        filters = [
            Review.employee_id == employee_id,
            Review.organization_id == employee.organization_id,
            Review.status == ReviewStatus.PUBLISHED,
        ]
        if rating is not None:
            filters.append(Review.overall_rating == rating)
        total = self.session.scalar(select(func.count(Review.id)).where(*filters)) or 0
        order = {
            "newest": Review.created_at.desc(),
            "oldest": Review.created_at.asc(),
            "highest_rating": Review.overall_rating.desc(),
            "lowest_rating": Review.overall_rating.asc(),
        }[sorting]
        statement = (
            select(Review)
            .options(
                selectinload(Review.client),
                selectinload(Review.service),
                selectinload(Review.reply).selectinload(ReviewReply.author),
            )
            .where(*filters)
            .order_by(order, Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def list_mine(
        self, actor: User, *, page: int, page_size: int
    ) -> tuple[list[Review], int]:
        filters = [Review.client_user_id == actor.id]
        total = self.session.scalar(select(func.count(Review.id)).where(*filters)) or 0
        statement = (
            select(Review)
            .options(
                selectinload(Review.client),
                selectinload(Review.service),
                selectinload(Review.reply).selectinload(ReviewReply.author),
            )
            .where(*filters)
            .order_by(Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def rating(self, employee_id: UUID, actor: User) -> dict:
        employee = self.session.get(Employee, employee_id)
        if employee is None:
            raise ReviewError("EMPLOYEE_NOT_FOUND", "Employee not found", 404)
        self._assert_tenant(actor, employee.organization_id)
        filters = [
            Review.employee_id == employee_id,
            Review.organization_id == employee.organization_id,
            Review.status == ReviewStatus.PUBLISHED,
        ]
        row = self.session.execute(
            select(
                func.avg(Review.overall_rating),
                func.count(Review.id),
                func.avg(Review.quality_rating),
                func.avg(Review.service_rating),
                func.avg(Review.punctuality_rating),
            ).where(*filters)
        ).one()
        distribution_rows = self.session.execute(
            select(Review.overall_rating, func.count(Review.id))
            .where(*filters)
            .group_by(Review.overall_rating)
        )
        return {
            "employee_id": employee_id,
            "average_rating": round(float(row[0]), 2) if row[0] is not None else None,
            "reviews_count": int(row[1]),
            "distribution": {**{key: 0 for key in range(1, 6)}, **{int(k): int(v) for k, v in distribution_rows}},
            "average_quality_rating": round(float(row[2]), 2) if row[2] is not None else None,
            "average_service_rating": round(float(row[3]), 2) if row[3] is not None else None,
            "average_punctuality_rating": round(float(row[4]), 2) if row[4] is not None else None,
        }

    def report(self, review_id: UUID, actor: User, payload) -> ReviewReport:
        review = self._get(review_id)
        self._assert_tenant(actor, review.organization_id)
        if review.status == ReviewStatus.HIDDEN:
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        if review.client_user_id == actor.id:
            raise ReviewError("CANNOT_REPORT_OWN_REVIEW", "You cannot report your own review", 409)
        report = ReviewReport(
            organization_id=review.organization_id,
            review_id=review.id,
            reporter_user_id=actor.id,
            reason=payload.reason.strip(),
            comment=payload.comment.strip() if payload.comment else None,
        )
        self.session.add(report)
        try:
            self.session.flush()
            self._audit(
                review,
                actor,
                ReviewAuditAction.REVIEW_REPORTED,
                payload.reason.strip(),
            )
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ReviewError(
                "REVIEW_ALREADY_REPORTED",
                "You already reported this review",
                409,
            ) from None
        return report

    def upsert_reply(self, review_id: UUID, actor: User, text: str) -> ReviewReply:
        review = self._get(review_id)
        self._assert_tenant(actor, review.organization_id)
        if actor.role == UserRole.EMPLOYEE:
            owns_employee = self.session.scalar(
                select(Employee.id).where(
                    Employee.id == review.employee_id,
                    Employee.user_id == actor.id,
                )
            )
            if owns_employee is None:
                raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        elif not self._is_admin(actor, review.organization_id):
            raise ReviewError("INSUFFICIENT_PERMISSIONS", "Insufficient permissions", 403)
        reply = self.session.scalar(
            select(ReviewReply).where(ReviewReply.review_id == review.id)
        )
        if reply is None:
            reply = ReviewReply(
                organization_id=review.organization_id,
                review_id=review.id,
                author_user_id=actor.id,
                text=text,
            )
            self.session.add(reply)
            action = ReviewAuditAction.REVIEW_REPLY_CREATED
        else:
            reply.author_user_id = actor.id
            reply.text = text
            action = ReviewAuditAction.REVIEW_REPLY_UPDATED
        self.session.flush()
        self._audit(review, actor, action)
        self.session.commit()
        self.session.refresh(reply)
        return reply

    def moderate(self, review_id: UUID, actor: User, status: ReviewStatus, reason: str) -> Review:
        review = self._get(review_id)
        if not self._is_admin(actor, review.organization_id):
            raise ReviewError("REVIEW_NOT_FOUND", "Review not found", 404)
        old_status = review.status
        review.status = status
        review.moderation_note = reason
        action = {
            ReviewStatus.PUBLISHED: ReviewAuditAction.REVIEW_RESTORED,
            ReviewStatus.HIDDEN: ReviewAuditAction.REVIEW_HIDDEN,
            ReviewStatus.FLAGGED: ReviewAuditAction.REVIEW_UPDATED,
        }[status]
        self._audit(review, actor, action, f"{old_status.value} -> {status.value}: {reason}")
        self.session.commit()
        return self._get(review.id)

    def list_admin(
        self,
        organization_id: UUID,
        actor: User,
        *,
        page: int,
        page_size: int,
        status: ReviewStatus | None,
    ) -> tuple[list[Review], int]:
        if not self._is_admin(actor, organization_id):
            raise ReviewError("REVIEW_NOT_FOUND", "Organization not found", 404)
        filters = [Review.organization_id == organization_id]
        if status is not None:
            filters.append(Review.status == status)
        total = self.session.scalar(select(func.count(Review.id)).where(*filters)) or 0
        statement = (
            select(Review)
            .options(
                selectinload(Review.client),
                selectinload(Review.service),
                selectinload(Review.reply).selectinload(ReviewReply.author),
                selectinload(Review.reports),
            )
            .where(*filters)
            .order_by(Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def resolve_report(
        self,
        report_id: UUID,
        actor: User,
        status: ReviewReportStatus,
    ) -> ReviewReport:
        report = self.session.get(ReviewReport, report_id)
        if report is None or not self._is_admin(actor, report.organization_id):
            raise ReviewError("REVIEW_REPORT_NOT_FOUND", "Review report not found", 404)
        report.status = status
        self.session.commit()
        self.session.refresh(report)
        return report

    def admin_dict(self, review: Review, actor: User) -> dict:
        item = self.public_dict(review, actor, private=True)
        item["moderation_note"] = review.moderation_note
        item["reports"] = [
            {
                "id": report.id,
                "review_id": report.review_id,
                "reporter_user_id": report.reporter_user_id,
                "reason": report.reason,
                "comment": report.comment,
                "status": report.status,
                "created_at": report.created_at,
            }
            for report in review.reports
        ]
        return item

    def analytics(
        self,
        organization_id: UUID,
        actor: User,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        employee_id: UUID | None = None,
        service_id: UUID | None = None,
        rating: int | None = None,
    ) -> dict:
        if not self._is_admin(actor, organization_id):
            raise ReviewError("REVIEW_NOT_FOUND", "Organization not found", 404)
        filters = [Review.organization_id == organization_id]
        if date_from:
            filters.append(Review.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        if date_to:
            filters.append(Review.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
        if employee_id:
            filters.append(Review.employee_id == employee_id)
        if service_id:
            filters.append(Review.service_id == service_id)
        if rating:
            filters.append(Review.overall_rating == rating)
        row = self.session.execute(
            select(
                func.count(Review.id),
                func.avg(case((Review.status == ReviewStatus.PUBLISHED, Review.overall_rating))),
                func.sum(case((Review.overall_rating <= 2, 1), else_=0)),
                func.sum(case((Review.status == ReviewStatus.FLAGGED, 1), else_=0)),
            ).where(*filters)
        ).one()
        published_filters = [*filters, Review.status == ReviewStatus.PUBLISHED]
        employees = self.session.execute(
            select(Employee.id, Employee.display_name, func.avg(Review.overall_rating), func.count(Review.id))
            .join(Review, Review.employee_id == Employee.id)
            .where(*published_filters)
            .group_by(Employee.id, Employee.display_name)
            .order_by(func.avg(Review.overall_rating).desc())
        )
        services = self.session.execute(
            select(Service.id, Service.name, func.avg(Review.overall_rating), func.count(Review.id))
            .join(Review, Review.service_id == Service.id)
            .where(*published_filters)
            .group_by(Service.id, Service.name)
            .order_by(func.avg(Review.overall_rating).desc())
        )
        day_expr = func.date(Review.created_at)
        trend_rows = self.session.execute(
            select(day_expr, func.avg(Review.overall_rating), func.count(Review.id))
            .where(*published_filters)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        return {
            "reviews_count": int(row[0] or 0),
            "average_rating": round(float(row[1]), 2) if row[1] is not None else None,
            "negative_reviews_count": int(row[2] or 0),
            "flagged_reviews_count": int(row[3] or 0),
            "by_employee": [
                {"id": item[0], "name": item[1], "average_rating": round(float(item[2]), 2), "reviews_count": int(item[3])}
                for item in employees
            ],
            "by_service": [
                {"id": item[0], "name": item[1], "average_rating": round(float(item[2]), 2), "reviews_count": int(item[3])}
                for item in services
            ],
            "trend": [
                {
                    "date": item[0] if isinstance(item[0], date) else date.fromisoformat(item[0]),
                    "average_rating": round(float(item[1]), 2),
                    "reviews_count": int(item[2]),
                }
                for item in trend_rows
            ],
        }

    def public_dict(self, review: Review, actor: User, *, private: bool = False) -> dict:
        is_owner = actor.id == review.client_user_id
        is_admin = self._is_admin(actor, review.organization_id)
        include_private = private or is_owner or is_admin
        client_name = "Anonymous"
        if not review.is_anonymous or include_private:
            client_name = f"{review.client.first_name} {review.client.last_name[:1]}."
        deadline = _utc(review.created_at) + self.edit_window
        reply = None
        if review.reply is not None:
            author_label = "Organization"
            employee = self.session.scalar(
                select(Employee).where(
                    Employee.user_id == review.reply.author_user_id,
                    Employee.organization_id == review.organization_id,
                )
            )
            if employee is not None:
                author_label = employee.display_name
            reply = {
                "id": review.reply.id,
                "author_user_id": review.reply.author_user_id if include_private else None,
                "author_label": author_label,
                "text": review.reply.text,
                "created_at": review.reply.created_at,
                "updated_at": review.reply.updated_at,
            }
        return {
            "id": review.id,
            "appointment_id": review.appointment_id if include_private else None,
            "employee_id": review.employee_id,
            "service_id": review.service_id,
            "service_name": review.service.name,
            "client_user_id": review.client_user_id if include_private else None,
            "client_display_name": client_name,
            "overall_rating": review.overall_rating,
            "quality_rating": review.quality_rating,
            "service_rating": review.service_rating,
            "punctuality_rating": review.punctuality_rating,
            "comment": review.comment,
            "is_anonymous": review.is_anonymous,
            "status": review.status if include_private else None,
            "can_edit": self._can_edit(review, actor),
            "edit_deadline": deadline if is_owner else None,
            "reply": reply,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "external_review_url_2gis": self.session.scalar(
                select(Organization.external_review_url_2gis).where(
                    Organization.id == review.organization_id
                )
            )
            if is_owner
            else None,
        }

    @staticmethod
    def page(items: list[dict], page: int, page_size: int, total: int) -> dict:
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": math.ceil(total / page_size) if total else 0,
        }
