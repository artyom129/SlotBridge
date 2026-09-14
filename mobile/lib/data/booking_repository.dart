import '../core/network/api_client.dart';
import '../domain/models.dart';

abstract interface class BookingRepository {
  Future<Availability> availability({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime date,
  });
  Future<Appointment> create({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime startsAt,
    required String idempotencyKey,
    String? note,
  });
  Future<List<Appointment>> list({String view = 'all'});
  Future<Appointment> detail(String id);
  Future<Appointment> cancel(String id, {String? reason});
  Future<Appointment> reschedule(
    String id, {
    required DateTime startsAt,
    String? reason,
  });
}

class ApiBookingRepository implements BookingRepository {
  ApiBookingRepository(this._api);

  final ApiClient _api;

  @override
  Future<Availability> availability({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime date,
  }) async {
    final dateValue =
        '${date.year.toString().padLeft(4, '0')}-'
        '${date.month.toString().padLeft(2, '0')}-'
        '${date.day.toString().padLeft(2, '0')}';
    final response = await _api.get(
      '/availability',
      queryParameters: {
        'branch_id': branchId,
        'employee_id': employeeId,
        'service_id': serviceId,
        'date': dateValue,
      },
    );
    return Availability.fromJson(response as JsonMap);
  }

  @override
  Future<Appointment> create({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime startsAt,
    required String idempotencyKey,
    String? note,
  }) async {
    final response = await _api.post(
      '/appointments',
      headers: {'Idempotency-Key': idempotencyKey},
      data: {
        'branch_id': branchId,
        'employee_id': employeeId,
        'service_id': serviceId,
        'starts_at': startsAt.toUtc().toIso8601String(),
        if (note != null && note.trim().isNotEmpty) 'client_note': note.trim(),
      },
    );
    return Appointment.fromJson(response as JsonMap);
  }

  @override
  Future<List<Appointment>> list({String view = 'all'}) async {
    final response = await _api.get(
      '/appointments/me',
      queryParameters: {'view': view},
    );
    return ((response as JsonMap)['items'] as List<dynamic>)
        .map((item) => Appointment.fromJson(item as JsonMap))
        .toList(growable: false);
  }

  @override
  Future<Appointment> detail(String id) async {
    final response = await _api.get('/appointments/$id');
    return Appointment.fromJson(response as JsonMap);
  }

  @override
  Future<Appointment> cancel(String id, {String? reason}) async {
    final response = await _api.post(
      '/appointments/$id/cancel',
      data: {
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      },
    );
    return Appointment.fromJson(response as JsonMap);
  }

  @override
  Future<Appointment> reschedule(
    String id, {
    required DateTime startsAt,
    String? reason,
  }) async {
    final response = await _api.post(
      '/appointments/$id/reschedule',
      data: {
        'starts_at': startsAt.toUtc().toIso8601String(),
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      },
    );
    return Appointment.fromJson(response as JsonMap);
  }
}
