import 'package:uuid/uuid.dart';

import '../core/network/api_client.dart';
import '../domain/models.dart';

class WaitlistRepository {
  WaitlistRepository(this.api);
  final ApiClient api;
  Future<List<WaitlistItem>> list() async {
    final response = await api.get('/waitlist/me') as JsonMap;
    return (response['items'] as List<dynamic>)
        .map((x) => WaitlistItem.fromJson(x as JsonMap))
        .toList();
  }

  Future<void> create({
    required String branchId,
    required String serviceId,
    required String employeeId,
    required DateTime start,
    required DateTime end,
  }) async {
    String d(DateTime x) =>
        '${x.year.toString().padLeft(4, '0')}-${x.month.toString().padLeft(2, '0')}-${x.day.toString().padLeft(2, '0')}';
    String t(DateTime x) =>
        '${x.hour.toString().padLeft(2, '0')}:${x.minute.toString().padLeft(2, '0')}:00';
    await api.post(
      '/waitlist',
      data: {
        'branch_id': branchId,
        'service_id': serviceId,
        'employee_id': employeeId,
        'preferred_date': d(start),
        'preferred_start_time': t(start),
        'preferred_end_time': t(end),
      },
    );
  }

  Future<void> accept(String id) async {
    await api.post(
      '/waitlist/$id/accept',
      headers: {'Idempotency-Key': const Uuid().v4()},
    );
  }
}
