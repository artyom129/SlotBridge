import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/domain/models.dart';

void main() {
  test(
    'appointment parser keeps UTC instant and branch wall clock separate',
    () {
      final appointment = Appointment.fromJson({
        'id': 'appointment-1',
        'organization_id': 'org-1',
        'branch': {'id': 'branch-1', 'name': 'Main Branch'},
        'employee': {'id': 'employee-1', 'name': 'Alex'},
        'service': {'id': 'service-1', 'name': 'Haircut'},
        'starts_at': '2099-01-05T04:00:00Z',
        'ends_at': '2099-01-05T05:00:00Z',
        'local_starts_at': '2099-01-05T09:00:00+05:00',
        'local_ends_at': '2099-01-05T10:00:00+05:00',
        'timezone': 'Asia/Almaty',
        'status': 'BOOKED',
        'client_note': null,
        'cancellation_reason': null,
        'cancelled_at': null,
        'status_history': [
          {
            'old_status': null,
            'new_status': 'BOOKED',
            'reason': 'Created',
            'created_at': '2099-01-01T00:00:00Z',
          },
        ],
      });

      expect(appointment.startsAt.toUtc().hour, 4);
      expect(appointment.localStartsAt.hour, 9);
      expect(appointment.localEndsAt.hour, 10);
      expect(appointment.timezone, 'Asia/Almaty');
      expect(appointment.history.single.newStatus, 'BOOKED');
    },
  );

  test('availability parser keeps absolute and displayed times', () {
    final availability = Availability.fromJson({
      'date': '2099-01-05',
      'timezone': 'Asia/Almaty',
      'service_duration_minutes': 60,
      'slots': [
        {
          'start': '2099-01-05T15:00:00+05:00',
          'end': '2099-01-05T16:00:00+05:00',
        },
      ],
    });

    expect(availability.slots.single.start.toUtc().hour, 10);
    expect(availability.slots.single.localStart.hour, 15);
  });
}
