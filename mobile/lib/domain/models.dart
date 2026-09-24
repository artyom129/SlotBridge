typedef JsonMap = Map<String, dynamic>;

DateTime parseWallClock(String value) {
  final match = RegExp(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?')
      .firstMatch(value);
  if (match == null) return DateTime.parse(value).toLocal();
  return DateTime(
    int.parse(match.group(1)!),
    int.parse(match.group(2)!),
    int.parse(match.group(3)!),
    int.parse(match.group(4)!),
    int.parse(match.group(5)!),
    int.parse(match.group(6) ?? '0'),
  );
}

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    this.phone,
  });

  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final String? phone;

  String get displayName => '$firstName $lastName'.trim();

  factory AppUser.fromJson(JsonMap json) => AppUser(
    id: json['id'] as String,
    email: json['email'] as String,
    firstName: json['first_name'] as String,
    lastName: json['last_name'] as String,
    role: json['role'] as String,
    phone: json['phone'] as String?,
  );
}

class Organization {
  const Organization({
    required this.id,
    required this.name,
    required this.timezone,
    required this.isActive,
    this.externalReviewUrl2gis,
  });

  final String id;
  final String name;
  final String timezone;
  final bool isActive;
  final String? externalReviewUrl2gis;

  factory Organization.fromJson(JsonMap json) => Organization(
    id: json['id'] as String,
    name: json['name'] as String,
    timezone: json['timezone'] as String,
    isActive: json['is_active'] as bool,
    externalReviewUrl2gis: json['external_review_url_2gis'] as String?,
  );
}

class Branch {
  const Branch({
    required this.id,
    required this.organizationId,
    required this.name,
    required this.address,
    required this.timezone,
    required this.isActive,
  });

  final String id;
  final String organizationId;
  final String name;
  final String address;
  final String? timezone;
  final bool isActive;

  factory Branch.fromJson(JsonMap json) => Branch(
    id: json['id'] as String,
    organizationId: json['organization_id'] as String,
    name: json['name'] as String,
    address: json['address'] as String,
    timezone: json['timezone'] as String?,
    isActive: json['is_active'] as bool,
  );
}

class Service {
  const Service({
    required this.id,
    required this.organizationId,
    required this.name,
    required this.description,
    required this.durationMinutes,
    required this.price,
    required this.isActive,
  });

  final String id;
  final String organizationId;
  final String name;
  final String description;
  final int durationMinutes;
  final double? price;
  final bool isActive;

  factory Service.fromJson(JsonMap json) => Service(
    id: json['id'] as String,
    organizationId: json['organization_id'] as String,
    name: json['name'] as String,
    description: json['description'] as String,
    durationMinutes: json['duration_minutes'] as int,
    price: json['price'] == null
        ? null
        : double.tryParse(json['price'].toString()),
    isActive: json['is_active'] as bool,
  );
}

class Employee {
  const Employee({
    required this.id,
    required this.organizationId,
    required this.branchId,
    required this.displayName,
    required this.isActive,
  });

  final String id;
  final String organizationId;
  final String branchId;
  final String displayName;
  final bool isActive;

  factory Employee.fromJson(JsonMap json) => Employee(
    id: json['id'] as String,
    organizationId: json['organization_id'] as String,
    branchId: json['branch_id'] as String,
    displayName: json['display_name'] as String,
    isActive: json['is_active'] as bool,
  );
}

class AvailabilitySlot {
  const AvailabilitySlot({
    required this.start,
    required this.end,
    required this.localStart,
    required this.localEnd,
  });

  final DateTime start;
  final DateTime end;
  final DateTime localStart;
  final DateTime localEnd;

  factory AvailabilitySlot.fromJson(JsonMap json) {
    final startValue = json['start'] as String;
    final endValue = json['end'] as String;
    return AvailabilitySlot(
      start: DateTime.parse(startValue),
      end: DateTime.parse(endValue),
      localStart: parseWallClock(startValue),
      localEnd: parseWallClock(endValue),
    );
  }
}

class RecommendedSlot {
  const RecommendedSlot({required this.slot, required this.reason});
  final AvailabilitySlot slot;
  final String reason;
  factory RecommendedSlot.fromJson(JsonMap json) => RecommendedSlot(
    slot: AvailabilitySlot.fromJson(json),
    reason: json['reason'] as String,
  );
}

class Availability {
  const Availability({
    required this.date,
    required this.timezone,
    required this.serviceDurationMinutes,
    required this.slots,
    this.recommendations = const [],
  });

  final DateTime date;
  final String timezone;
  final int serviceDurationMinutes;
  final List<AvailabilitySlot> slots;
  final List<RecommendedSlot> recommendations;

  factory Availability.fromJson(JsonMap json) => Availability(
    date: DateTime.parse(json['date'] as String),
    timezone: json['timezone'] as String,
    serviceDurationMinutes: json['service_duration_minutes'] as int,
    slots: (json['slots'] as List<dynamic>)
        .map((item) => AvailabilitySlot.fromJson(item as JsonMap))
        .toList(growable: false),
    recommendations: ((json['recommendations'] as List<dynamic>?) ?? const [])
        .map((item) => RecommendedSlot.fromJson(item as JsonMap))
        .toList(growable: false),
  );
}

class ResourceSummary {
  const ResourceSummary({required this.id, required this.name});

  final String id;
  final String name;

  factory ResourceSummary.fromJson(JsonMap json) =>
      ResourceSummary(id: json['id'] as String, name: json['name'] as String);
}

class StatusHistory {
  const StatusHistory({
    required this.oldStatus,
    required this.newStatus,
    required this.reason,
    required this.createdAt,
  });

  final String? oldStatus;
  final String newStatus;
  final String? reason;
  final DateTime createdAt;

  factory StatusHistory.fromJson(JsonMap json) => StatusHistory(
    oldStatus: json['old_status'] as String?,
    newStatus: json['new_status'] as String,
    reason: json['reason'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}

class Appointment {
  const Appointment({
    required this.id,
    required this.organizationId,
    required this.branch,
    required this.employee,
    required this.service,
    required this.startsAt,
    required this.endsAt,
    required this.localStartsAt,
    required this.localEndsAt,
    required this.timezone,
    required this.status,
    required this.clientNote,
    required this.cancellationReason,
    required this.cancelledAt,
    required this.history,
    this.reviewId,
  });

  final String id;
  final String organizationId;
  final ResourceSummary branch;
  final ResourceSummary employee;
  final ResourceSummary service;
  final DateTime startsAt;
  final DateTime endsAt;
  final DateTime localStartsAt;
  final DateTime localEndsAt;
  final String timezone;
  final String status;
  final String? clientNote;
  final String? cancellationReason;
  final DateTime? cancelledAt;
  final List<StatusHistory> history;
  final String? reviewId;

  bool get isCancelled => status == 'CANCELLED';
  bool get canClientChange =>
      !isCancelled &&
      (status == 'BOOKED' || status == 'CONFIRMED') &&
      startsAt.isAfter(DateTime.now().toUtc());

  factory Appointment.fromJson(JsonMap json) => Appointment(
    id: json['id'] as String,
    organizationId: json['organization_id'] as String,
    branch: ResourceSummary.fromJson(json['branch'] as JsonMap),
    employee: ResourceSummary.fromJson(json['employee'] as JsonMap),
    service: ResourceSummary.fromJson(json['service'] as JsonMap),
    startsAt: DateTime.parse(json['starts_at'] as String),
    endsAt: DateTime.parse(json['ends_at'] as String),
    localStartsAt: parseWallClock(json['local_starts_at'] as String),
    localEndsAt: parseWallClock(json['local_ends_at'] as String),
    timezone: json['timezone'] as String,
    status: json['status'] as String,
    clientNote: json['client_note'] as String?,
    cancellationReason: json['cancellation_reason'] as String?,
    cancelledAt: json['cancelled_at'] == null
        ? null
        : DateTime.parse(json['cancelled_at'] as String),
    history: ((json['status_history'] as List<dynamic>?) ?? const [])
        .map((item) => StatusHistory.fromJson(item as JsonMap))
        .toList(growable: false),
    reviewId: json['review_id'] as String?,
  );
}

class ReviewReply {
  const ReviewReply({
    required this.authorLabel,
    required this.text,
    required this.createdAt,
  });

  final String authorLabel;
  final String text;
  final DateTime createdAt;

  factory ReviewReply.fromJson(JsonMap json) => ReviewReply(
    authorLabel: json['author_label'] as String,
    text: json['text'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}

class Review {
  const Review({
    required this.id,
    required this.appointmentId,
    required this.employeeId,
    required this.serviceId,
    required this.serviceName,
    required this.clientDisplayName,
    required this.overallRating,
    required this.qualityRating,
    required this.serviceRating,
    required this.punctualityRating,
    required this.comment,
    required this.isAnonymous,
    required this.canEdit,
    required this.editDeadline,
    required this.reply,
    required this.createdAt,
    required this.externalReviewUrl2gis,
  });

  final String id;
  final String? appointmentId;
  final String employeeId;
  final String serviceId;
  final String? serviceName;
  final String clientDisplayName;
  final int overallRating;
  final int? qualityRating;
  final int? serviceRating;
  final int? punctualityRating;
  final String? comment;
  final bool isAnonymous;
  final bool canEdit;
  final DateTime? editDeadline;
  final ReviewReply? reply;
  final DateTime createdAt;
  final String? externalReviewUrl2gis;

  factory Review.fromJson(JsonMap json) => Review(
    id: json['id'] as String,
    appointmentId: json['appointment_id'] as String?,
    employeeId: json['employee_id'] as String,
    serviceId: json['service_id'] as String,
    serviceName: json['service_name'] as String?,
    clientDisplayName: json['client_display_name'] as String,
    overallRating: json['overall_rating'] as int,
    qualityRating: json['quality_rating'] as int?,
    serviceRating: json['service_rating'] as int?,
    punctualityRating: json['punctuality_rating'] as int?,
    comment: json['comment'] as String?,
    isAnonymous: json['is_anonymous'] as bool,
    canEdit: json['can_edit'] as bool? ?? false,
    editDeadline: json['edit_deadline'] == null
        ? null
        : DateTime.parse(json['edit_deadline'] as String),
    reply: json['reply'] == null
        ? null
        : ReviewReply.fromJson(json['reply'] as JsonMap),
    createdAt: DateTime.parse(json['created_at'] as String),
    externalReviewUrl2gis: json['external_review_url_2gis'] as String?,
  );
}

class EmployeeRating {
  const EmployeeRating({
    required this.employeeId,
    required this.averageRating,
    required this.reviewsCount,
    required this.distribution,
    required this.averageQualityRating,
    required this.averageServiceRating,
    required this.averagePunctualityRating,
  });

  final String employeeId;
  final double? averageRating;
  final int reviewsCount;
  final Map<int, int> distribution;
  final double? averageQualityRating;
  final double? averageServiceRating;
  final double? averagePunctualityRating;

  factory EmployeeRating.fromJson(JsonMap json) => EmployeeRating(
    employeeId: json['employee_id'] as String,
    averageRating: (json['average_rating'] as num?)?.toDouble(),
    reviewsCount: json['reviews_count'] as int,
    distribution: (json['distribution'] as JsonMap).map(
      (key, value) => MapEntry(int.parse(key), value as int),
    ),
    averageQualityRating: (json['average_quality_rating'] as num?)?.toDouble(),
    averageServiceRating: (json['average_service_rating'] as num?)?.toDouble(),
    averagePunctualityRating: (json['average_punctuality_rating'] as num?)
        ?.toDouble(),
  );
}

class ReviewPage {
  const ReviewPage({required this.items, required this.total});
  final List<Review> items;
  final int total;

  factory ReviewPage.fromJson(JsonMap json) => ReviewPage(
    items: (json['items'] as List<dynamic>)
        .map((item) => Review.fromJson(item as JsonMap))
        .toList(growable: false),
    total: json['total'] as int,
  );
}

class CatalogBootstrap {
  const CatalogBootstrap({
    required this.organization,
    required this.branch,
    required this.services,
  });

  final Organization organization;
  final Branch branch;
  final List<Service> services;
}

class WaitlistItem {
  const WaitlistItem({
    required this.id,
    required this.status,
    required this.serviceName,
    required this.employeeName,
    required this.matchedStartsAt,
  });
  final String id, status;
  final String? serviceName, employeeName;
  final DateTime? matchedStartsAt;
  factory WaitlistItem.fromJson(JsonMap json) => WaitlistItem(
    id: json['id'] as String,
    status: json['status'] as String,
    serviceName: json['service_name'] as String?,
    employeeName: json['employee_name'] as String?,
    matchedStartsAt: json['matched_starts_at'] == null
        ? null
        : DateTime.parse(json['matched_starts_at'] as String),
  );
}

class JourneyStep {
  const JourneyStep({
    required this.service,
    required this.employee,
    required this.startsAt,
    required this.endsAt,
    required this.localStartsAt,
    required this.localEndsAt,
  });

  final ResourceSummary service;
  final ResourceSummary employee;
  final DateTime startsAt;
  final DateTime endsAt;
  final DateTime localStartsAt;
  final DateTime localEndsAt;

  factory JourneyStep.fromJson(JsonMap json) => JourneyStep(
    service: ResourceSummary.fromJson(json['service'] as JsonMap),
    employee: ResourceSummary.fromJson(json['employee'] as JsonMap),
    startsAt: DateTime.parse(json['starts_at'] as String),
    endsAt: DateTime.parse(json['ends_at'] as String),
    localStartsAt: parseWallClock(json['local_starts_at'] as String),
    localEndsAt: parseWallClock(json['local_ends_at'] as String),
  );
}

class JourneyRoute {
  const JourneyRoute({
    required this.strategy,
    required this.steps,
    required this.startsAt,
    required this.endsAt,
    required this.totalMinutes,
    required this.waitMinutes,
    required this.employeeCount,
  });

  final String strategy;
  final List<JourneyStep> steps;
  final DateTime startsAt;
  final DateTime endsAt;
  final int totalMinutes;
  final int waitMinutes;
  final int employeeCount;

  factory JourneyRoute.fromJson(JsonMap json) => JourneyRoute(
    strategy: json['strategy'] as String,
    steps: (json['steps'] as List<dynamic>)
        .map((item) => JourneyStep.fromJson(item as JsonMap))
        .toList(growable: false),
    startsAt: DateTime.parse(json['starts_at'] as String),
    endsAt: DateTime.parse(json['ends_at'] as String),
    totalMinutes: json['total_minutes'] as int,
    waitMinutes: json['wait_minutes'] as int,
    employeeCount: json['employee_count'] as int,
  );
}

class JourneyPlan {
  const JourneyPlan({required this.timezone, required this.routes});

  final String timezone;
  final List<JourneyRoute> routes;

  factory JourneyPlan.fromJson(JsonMap json) => JourneyPlan(
    timezone: json['timezone'] as String,
    routes: (json['routes'] as List<dynamic>)
        .map((item) => JourneyRoute.fromJson(item as JsonMap))
        .toList(growable: false),
  );
}
