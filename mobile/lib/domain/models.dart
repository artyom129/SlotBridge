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
  });

  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final String role;

  String get displayName => '$firstName $lastName'.trim();

  factory AppUser.fromJson(JsonMap json) => AppUser(
    id: json['id'] as String,
    email: json['email'] as String,
    firstName: json['first_name'] as String,
    lastName: json['last_name'] as String,
    role: json['role'] as String,
  );
}

class Organization {
  const Organization({
    required this.id,
    required this.name,
    required this.timezone,
    required this.isActive,
  });

  final String id;
  final String name;
  final String timezone;
  final bool isActive;

  factory Organization.fromJson(JsonMap json) => Organization(
    id: json['id'] as String,
    name: json['name'] as String,
    timezone: json['timezone'] as String,
    isActive: json['is_active'] as bool,
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

class Availability {
  const Availability({
    required this.date,
    required this.timezone,
    required this.serviceDurationMinutes,
    required this.slots,
  });

  final DateTime date;
  final String timezone;
  final int serviceDurationMinutes;
  final List<AvailabilitySlot> slots;

  factory Availability.fromJson(JsonMap json) => Availability(
    date: DateTime.parse(json['date'] as String),
    timezone: json['timezone'] as String,
    serviceDurationMinutes: json['service_duration_minutes'] as int,
    slots: (json['slots'] as List<dynamic>)
        .map((item) => AvailabilitySlot.fromJson(item as JsonMap))
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
