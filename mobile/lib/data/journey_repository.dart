import '../core/network/api_client.dart';
import '../domain/models.dart';

abstract interface class JourneyRepository {
  Future<JourneyPlan> plan({
    required String branchId,
    required List<String> serviceIds,
    required DateTime date,
    required TimeOfDayValue after,
    required TimeOfDayValue before,
  });

  Future<List<Appointment>> book({
    required String branchId,
    required JourneyRoute route,
    required String idempotencyKey,
  });
}

class TimeOfDayValue {
  const TimeOfDayValue(this.hour, this.minute);

  final int hour;
  final int minute;

  String get apiValue =>
      '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
}

class ApiJourneyRepository implements JourneyRepository {
  ApiJourneyRepository(this._api);

  final ApiClient _api;

  @override
  Future<JourneyPlan> plan({
    required String branchId,
    required List<String> serviceIds,
    required DateTime date,
    required TimeOfDayValue after,
    required TimeOfDayValue before,
  }) async {
    final dateValue =
        '${date.year.toString().padLeft(4, '0')}-'
        '${date.month.toString().padLeft(2, '0')}-'
        '${date.day.toString().padLeft(2, '0')}';
    final response = await _api.post(
      '/journeys/plan',
      data: {
        'branch_id': branchId,
        'service_ids': serviceIds,
        'date': dateValue,
        'after_time': after.apiValue,
        'before_time': before.apiValue,
      },
    );
    return JourneyPlan.fromJson(response as JsonMap);
  }

  @override
  Future<List<Appointment>> book({
    required String branchId,
    required JourneyRoute route,
    required String idempotencyKey,
  }) async {
    final response = await _api.post(
      '/journeys/book',
      headers: {'Idempotency-Key': idempotencyKey},
      data: {
        'branch_id': branchId,
        'steps': route.steps
            .map(
              (step) => {
                'service_id': step.service.id,
                'employee_id': step.employee.id,
                'starts_at': step.startsAt.toUtc().toIso8601String(),
              },
            )
            .toList(growable: false),
      },
    );
    return ((response as JsonMap)['appointments'] as List<dynamic>)
        .map((item) => Appointment.fromJson(item as JsonMap))
        .toList(growable: false);
  }
}
