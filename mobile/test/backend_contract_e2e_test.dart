import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/network/api_client.dart';
import 'package:slotbridge_mobile/core/storage/token_storage.dart';
import 'package:slotbridge_mobile/data/auth_repository.dart';
import 'package:slotbridge_mobile/data/booking_repository.dart';
import 'package:slotbridge_mobile/data/catalog_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:uuid/uuid.dart';

class _MemoryTokenStorage implements TokenStorage {
  String? token;

  @override
  Future<void> clear() async => token = null;

  @override
  Future<String?> read() async => token;

  @override
  Future<void> write(String value) async => token = value;
}

void main() {
  final baseUrl = Platform.environment['SLOTBRIDGE_E2E_BASE_URL'];
  test(
    'real API contract covers registration, catalog, booking, list, detail, reschedule and cancel',
    () async {
      final storage = _MemoryTokenStorage();
      final api = ApiClient(
        storage,
        dio: Dio(
          BaseOptions(
            baseUrl: baseUrl!,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 20),
          ),
        ),
      );
      final auth = ApiAuthRepository(api, storage);
      final catalogRepository = ApiCatalogRepository(api);
      final booking = ApiBookingRepository(api);

      final registrationEmail = 'mobile-e2e-${const Uuid().v4()}@example.com';
      final registered = await auth.register(
        firstName: 'Анна',
        lastName: 'Смирнова',
        email: registrationEmail,
        password: 'StrongPass123!',
        phone: '+7 700 000-00-00',
      );
      expect(registered.email, registrationEmail);
      expect(registered.role, 'CLIENT');
      expect(storage.token, isNotEmpty);

      final restoredSession = ApiAuthRepository(api, storage);
      expect(await restoredSession.hasSession(), isTrue);
      expect((await restoredSession.currentUser()).email, registrationEmail);
      await restoredSession.logout();

      final signedIn = await auth.login(registrationEmail, 'StrongPass123!');
      expect(signedIn.email, registrationEmail);
      expect(signedIn.role, 'CLIENT');

      final catalog = await catalogRepository.loadBootstrap();
      Service? chosenService;
      Employee? chosenEmployee;
      Availability? chosenAvailability;
      for (final service in catalog.services) {
        final employees = await catalogRepository.employeesForService(
          catalog.organization,
          catalog.branch,
          service,
        );
        for (final employee in employees) {
          for (var offset = 1; offset <= 14; offset++) {
            final date = DateTime.now().add(Duration(days: offset));
            final availability = await booking.availability(
              branchId: catalog.branch.id,
              employeeId: employee.id,
              serviceId: service.id,
              date: date,
            );
            if (availability.slots.length >= 2) {
              chosenService = service;
              chosenEmployee = employee;
              chosenAvailability = availability;
              break;
            }
          }
          if (chosenAvailability != null) break;
        }
        if (chosenAvailability != null) break;
      }

      expect(chosenService, isNotNull);
      expect(chosenEmployee, isNotNull);
      expect(chosenAvailability, isNotNull);
      final originalSlot = chosenAvailability!.slots.first;
      final targetSlot = chosenAvailability.slots.last;
      final key = const Uuid().v4();

      final created = await booking.create(
        branchId: catalog.branch.id,
        employeeId: chosenEmployee!.id,
        serviceId: chosenService!.id,
        startsAt: originalSlot.start,
        idempotencyKey: key,
        note: 'Проверка мобильной записи',
      );
      expect(created.status, 'BOOKED');
      expect(
        (await booking.list(view: 'upcoming'))
            .any((item) => item.id == created.id),
        isTrue,
      );
      expect((await booking.detail(created.id)).service.id, chosenService.id);

      final moved = await booking.reschedule(
        created.id,
        startsAt: targetSlot.start,
        reason: 'Проверка переноса записи',
      );
      expect(moved.startsAt.toUtc(), targetSlot.start.toUtc());

      final replay = await booking.create(
        branchId: catalog.branch.id,
        employeeId: chosenEmployee.id,
        serviceId: chosenService.id,
        startsAt: originalSlot.start,
        idempotencyKey: key,
        note: 'Проверка мобильной записи',
      );
      expect(replay.id, created.id);

      final cancelled = await booking.cancel(
        created.id,
        reason: 'Проверка отмены записи',
      );
      expect(cancelled.status, 'CANCELLED');
      expect(
        (await booking.detail(created.id)).cancellationReason,
        'Проверка отмены записи',
      );

      final afterCancellation = await booking.availability(
        branchId: catalog.branch.id,
        employeeId: chosenEmployee.id,
        serviceId: chosenService.id,
        date: targetSlot.localStart,
      );
      expect(
        afterCancellation.slots.any(
          (slot) => slot.start.toUtc() == targetSlot.start.toUtc(),
        ),
        isTrue,
      );
    },
    skip: baseUrl == null
        ? 'Set SLOTBRIDGE_E2E_BASE_URL to run against the isolated FastAPI backend.'
        : false,
  );
}
