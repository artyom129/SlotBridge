import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/data/booking_repository.dart';
import 'package:slotbridge_mobile/data/catalog_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/booking/booking_controller.dart';

const organization = Organization(
  id: 'org',
  name: 'Demo',
  timezone: 'UTC',
  isActive: true,
);
const branch = Branch(
  id: 'branch',
  organizationId: 'org',
  name: 'Main',
  address: 'Address',
  timezone: 'UTC',
  isActive: true,
);
const service = Service(
  id: 'service',
  organizationId: 'org',
  name: 'Haircut',
  description: 'Demo',
  durationMinutes: 60,
  price: 45,
  isActive: true,
);
const employee = Employee(
  id: 'employee',
  organizationId: 'org',
  branchId: 'branch',
  displayName: 'Alex',
  isActive: true,
);
final slot = AvailabilitySlot(
  start: DateTime.utc(2099, 1, 5, 15),
  end: DateTime.utc(2099, 1, 5, 16),
  localStart: DateTime(2099, 1, 5, 15),
  localEnd: DateTime(2099, 1, 5, 16),
);

class _CatalogRepository implements CatalogRepository {
  @override
  Future<CatalogBootstrap> loadBootstrap() async => const CatalogBootstrap(
    organization: organization,
    branch: branch,
    services: [service],
  );

  @override
  Future<List<Employee>> employeesForService(
    Organization organization,
    Branch branch,
    Service service,
  ) async => const [employee];
}

class _BookingRepository implements BookingRepository {
  final keys = <String>[];
  var createAttempts = 0;

  @override
  Future<Availability> availability({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime date,
  }) async => Availability(
    date: date,
    timezone: 'UTC',
    serviceDurationMinutes: 60,
    slots: [slot],
  );

  @override
  Future<Appointment> create({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime startsAt,
    required String idempotencyKey,
    String? note,
  }) async {
    keys.add(idempotencyKey);
    createAttempts++;
    if (createAttempts == 1) throw const AppException('Network interrupted');
    return Appointment(
      id: 'appointment',
      organizationId: 'org',
      branch: const ResourceSummary(id: 'branch', name: 'Main'),
      employee: const ResourceSummary(id: 'employee', name: 'Alex'),
      service: const ResourceSummary(id: 'service', name: 'Haircut'),
      startsAt: startsAt,
      endsAt: startsAt.add(const Duration(hours: 1)),
      localStartsAt: slot.localStart,
      localEndsAt: slot.localEnd,
      timezone: 'UTC',
      status: 'BOOKED',
      clientNote: note,
      cancellationReason: null,
      cancelledAt: null,
      history: const [],
    );
  }

  @override
  Future<Appointment> cancel(String id, {String? reason}) =>
      throw UnimplementedError();
  @override
  Future<Appointment> detail(String id) => throw UnimplementedError();
  @override
  Future<List<Appointment>> list({String view = 'all'}) =>
      throw UnimplementedError();
  @override
  Future<Appointment> reschedule(
    String id, {
    required DateTime startsAt,
    String? reason,
  }) => throw UnimplementedError();
}

void main() {
  test(
    'conflict rescue refreshes availability and uses a new key for alternative',
    () async {
      final bookingRepository = _BookingRepository();
      final container = ProviderContainer(
        overrides: [
          catalogRepositoryProvider.overrideWithValue(_CatalogRepository()),
          bookingRepositoryProvider.overrideWithValue(bookingRepository),
        ],
      );
      addTearDown(container.dispose);
      final controller = container.read(bookingControllerProvider.notifier);

      await controller.load();
      await controller.selectService(service);
      controller.selectEmployee(employee);
      await controller.selectDate(DateTime(2099, 1, 5));
      controller.selectSlot(slot);

      expect(await controller.submit('Window seat'), isNull);
      final rescued = container.read(bookingControllerProvider);
      expect(rescued.step, 3);
      expect(rescued.availability, isNotNull);
      expect(rescued.idempotencyKey, isNull);

      controller.selectSlot(slot);
      final appointment = await controller.submit('Window seat');
      expect(appointment?.id, 'appointment');
      expect(bookingRepository.keys, hasLength(2));
      expect(bookingRepository.keys[0], isNot(bookingRepository.keys[1]));
    },
  );
}
