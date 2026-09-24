from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models import (
    AppointmentAuditAction,
    AppointmentStatus,
    ReviewReportStatus,
    ReviewStatus,
    UserRole,
    WaitlistStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name must not be blank")
        return stripped


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=32)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=120)
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name must not be blank")
        return stripped

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("Unknown IANA timezone") from None
        return value


class OrganizationOut(ORMModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    is_active: bool
    external_review_url_2gis: str | None = None
    created_at: datetime
    updated_at: datetime


class BranchOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    address: str
    timezone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    duration_minutes: int
    price: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeOut(ORMModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    branch_id: UUID
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LocalRecurringInterval(BaseModel):
    employee_id: UUID
    branch_id: UUID
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, ..., 6=Sunday")
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def validate_interval(self) -> "LocalRecurringInterval":
        if self.start_time.tzinfo is not None or self.end_time.tzinfo is not None:
            raise ValueError("Recurring schedule times must be local wall-clock times")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class WorkScheduleCreate(LocalRecurringInterval):
    pass


class WorkScheduleOut(ORMModel):
    id: UUID
    employee_id: UUID
    branch_id: UUID
    organization_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ScheduleBreakCreate(LocalRecurringInterval):
    pass


class ScheduleBreakOut(WorkScheduleOut):
    pass


class ScheduleExceptionCreate(BaseModel):
    employee_id: UUID
    branch_id: UUID
    local_date: date
    is_day_off: bool = False
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_shape(self) -> "ScheduleExceptionCreate":
        if self.is_day_off:
            if self.start_time is not None or self.end_time is not None:
                raise ValueError("Day-off exception cannot contain a time interval")
            return self
        if self.start_time is None or self.end_time is None:
            raise ValueError("Replacement exception requires start_time and end_time")
        if self.start_time.tzinfo is not None or self.end_time.tzinfo is not None:
            raise ValueError("Exception times must be local wall-clock times")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class ScheduleExceptionOut(ORMModel):
    id: UUID
    employee_id: UUID
    branch_id: UUID
    organization_id: UUID
    local_date: date
    is_day_off: bool
    start_time: time | None
    end_time: time | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BlockedSlotCreate(BaseModel):
    employee_id: UUID
    branch_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reason: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_and_normalize_interval(self) -> "BlockedSlotCreate":
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at must be before ends_at")
        self.starts_at = self.starts_at.astimezone(timezone.utc)
        self.ends_at = self.ends_at.astimezone(timezone.utc)
        return self


class BlockedSlotOut(ORMModel):
    id: UUID
    employee_id: UUID
    branch_id: UUID
    organization_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reason: str | None
    created_by_user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def normalize_stored_instant(cls, value: datetime) -> datetime:
        # PostgreSQL returns aware timestamptz values. SQLite drops tzinfo, so tests and
        # supported local development treat those persisted values as UTC explicitly.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AvailabilitySlot(BaseModel):
    start: datetime
    end: datetime


class AvailabilityResponse(BaseModel):
    date: date
    timezone: str
    service_duration_minutes: int
    slot_interval_minutes: int
    slots: list[AvailabilitySlot]
    recommendations: list["RecommendedSlot"] = []


class RecommendedSlot(AvailabilitySlot):
    reason: Literal["BEST_FIT", "EARLIEST", "FILL_GAP"]


class WaitlistCreateRequest(BaseModel):
    branch_id: UUID
    service_id: UUID
    employee_id: UUID | None = None
    preferred_date: date
    preferred_start_time: time
    preferred_end_time: time

    @model_validator(mode="after")
    def validate_interval(self):
        if self.preferred_start_time >= self.preferred_end_time:
            raise ValueError("preferred_start_time must be before preferred_end_time")
        return self


class WaitlistOut(ORMModel):
    id: UUID
    organization_id: UUID
    client_user_id: UUID
    branch_id: UUID
    service_id: UUID
    employee_id: UUID | None
    preferred_date: date
    preferred_start_time: time
    preferred_end_time: time
    status: WaitlistStatus
    matched_employee_id: UUID | None
    matched_starts_at: datetime | None
    created_at: datetime
    updated_at: datetime
    service_name: str | None = None
    employee_name: str | None = None


class WaitlistListResponse(BaseModel):
    items: list[WaitlistOut]


class AppointmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    employee_id: UUID
    service_id: UUID
    starts_at: AwareDatetime
    client_note: str | None = Field(default=None, max_length=1000)

    @field_validator("starts_at", mode="after")
    @classmethod
    def normalize_start(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class AppointmentCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class AppointmentRescheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("starts_at", mode="after")
    @classmethod
    def normalize_start(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class AppointmentStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AppointmentStatus
    reason: str | None = Field(default=None, max_length=500)


class AppointmentResourceOut(BaseModel):
    id: UUID
    name: str


class AppointmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    client_user_id: UUID
    branch: AppointmentResourceOut
    employee: AppointmentResourceOut
    service: AppointmentResourceOut
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    timezone: str
    local_starts_at: AwareDatetime
    local_ends_at: AwareDatetime
    status: AppointmentStatus
    client_note: str | None
    cancellation_reason: str | None
    cancelled_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    review_id: UUID | None = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def normalize_metadata_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AppointmentStatusHistoryOut(ORMModel):
    id: UUID
    old_status: AppointmentStatus | None
    new_status: AppointmentStatus
    changed_by_user_id: UUID
    reason: str | None
    created_at: AwareDatetime

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AppointmentAuditOut(ORMModel):
    id: UUID
    action: AppointmentAuditAction
    changed_by_user_id: UUID
    reason: str | None
    old_starts_at: AwareDatetime | None
    old_ends_at: AwareDatetime | None
    new_starts_at: AwareDatetime | None
    new_ends_at: AwareDatetime | None
    created_at: AwareDatetime

    @field_validator(
        "old_starts_at",
        "old_ends_at",
        "new_starts_at",
        "new_ends_at",
        "created_at",
        mode="before",
    )
    @classmethod
    def normalize_audit_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AppointmentDetailOut(AppointmentOut):
    status_history: list[AppointmentStatusHistoryOut]
    audit_events: list[AppointmentAuditOut]


class AppointmentListResponse(BaseModel):
    items: list[AppointmentOut]


class ReviewCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    appointment_id: UUID
    overall_rating: int = Field(ge=1, le=5)
    quality_rating: int | None = Field(default=None, ge=1, le=5)
    service_rating: int | None = Field(default=None, ge=1, le=5)
    punctuality_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=5000)
    is_anonymous: bool = False

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReviewUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_rating: int | None = Field(default=None, ge=1, le=5)
    quality_rating: int | None = Field(default=None, ge=1, le=5)
    service_rating: int | None = Field(default=None, ge=1, le=5)
    punctuality_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=5000)
    is_anonymous: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ReviewUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one review field is required")
        if "overall_rating" in self.model_fields_set and self.overall_rating is None:
            raise ValueError("overall_rating cannot be null")
        return self

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReviewReplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reply must not be blank")
        return stripped


class ReviewReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReviewStatus
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_moderation_status(cls, value: ReviewStatus) -> ReviewStatus:
        if value not in {ReviewStatus.PUBLISHED, ReviewStatus.HIDDEN, ReviewStatus.FLAGGED}:
            raise ValueError("Unsupported moderation status")
        return value


class ReviewReplyOut(ORMModel):
    id: UUID
    author_user_id: UUID | None = None
    author_label: str
    text: str
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ReviewOut(BaseModel):
    id: UUID
    appointment_id: UUID | None = None
    employee_id: UUID
    service_id: UUID
    service_name: str | None = None
    client_user_id: UUID | None = None
    client_display_name: str
    overall_rating: int
    quality_rating: int | None
    service_rating: int | None
    punctuality_rating: int | None
    comment: str | None
    is_anonymous: bool
    status: ReviewStatus | None = None
    can_edit: bool = False
    edit_deadline: AwareDatetime | None = None
    reply: ReviewReplyOut | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    external_review_url_2gis: str | None = None

    @field_validator("created_at", "updated_at", "edit_deadline", mode="before")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ReviewListResponse(BaseModel):
    items: list[ReviewOut]
    page: int
    page_size: int
    total: int
    pages: int


class EmployeeRatingOut(BaseModel):
    employee_id: UUID
    average_rating: float | None
    reviews_count: int
    distribution: dict[int, int]
    average_quality_rating: float | None
    average_service_rating: float | None
    average_punctuality_rating: float | None


class ReviewReportOut(ORMModel):
    id: UUID
    review_id: UUID
    reporter_user_id: UUID
    reason: str
    comment: str | None
    status: ReviewReportStatus
    created_at: AwareDatetime

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ReviewReportStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReviewReportStatus

    @field_validator("status")
    @classmethod
    def require_closed_status(cls, value: ReviewReportStatus) -> ReviewReportStatus:
        if value == ReviewReportStatus.OPEN:
            raise ValueError("Use RESOLVED or DISMISSED")
        return value


class AdminReviewOut(ReviewOut):
    moderation_note: str | None = None
    reports: list[ReviewReportOut] = Field(default_factory=list)


class AdminReviewListResponse(BaseModel):
    items: list[AdminReviewOut]
    page: int
    page_size: int
    total: int
    pages: int


class RatingBreakdownItem(BaseModel):
    id: UUID
    name: str
    average_rating: float | None
    reviews_count: int


class RatingTrendPoint(BaseModel):
    date: date
    average_rating: float
    reviews_count: int


class ReviewAnalyticsOut(BaseModel):
    reviews_count: int
    average_rating: float | None
    negative_reviews_count: int
    flagged_reviews_count: int
    by_employee: list[RatingBreakdownItem]
    by_service: list[RatingBreakdownItem]
    trend: list[RatingTrendPoint]


class ReviewAiSummaryOut(BaseModel):
    summary: str
    generated_by: Literal["gemini", "fallback"]
    disclaimer: str
