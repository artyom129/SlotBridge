import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../core/providers.dart';
import '../../domain/models.dart';
import '../appointments/appointment_providers.dart';

final bookingControllerProvider =
    NotifierProvider<BookingController, BookingState>(BookingController.new);

class BookingState {
  const BookingState({
    this.step = 0,
    this.isLoading = false,
    this.isSubmitting = false,
    this.catalog,
    this.service,
    this.employees = const [],
    this.employee,
    this.date,
    this.availability,
    this.slot,
    this.idempotencyKey,
    this.error,
  });

  final int step;
  final bool isLoading;
  final bool isSubmitting;
  final CatalogBootstrap? catalog;
  final Service? service;
  final List<Employee> employees;
  final Employee? employee;
  final DateTime? date;
  final Availability? availability;
  final AvailabilitySlot? slot;
  final String? idempotencyKey;
  final Object? error;
}

class BookingController extends Notifier<BookingState> {
  @override
  BookingState build() => const BookingState();

  Future<void> load() async {
    if (state.catalog != null || state.isLoading) return;
    state = const BookingState(isLoading: true);
    try {
      final catalog = await ref.read(catalogRepositoryProvider).loadBootstrap();
      state = BookingState(catalog: catalog);
    } catch (error) {
      state = BookingState(error: error);
    }
  }

  Future<void> selectService(Service service) async {
    final catalog = state.catalog;
    if (catalog == null) return;
    state = BookingState(
      step: 1,
      isLoading: true,
      catalog: catalog,
      service: service,
    );
    try {
      final employees = await ref
          .read(catalogRepositoryProvider)
          .employeesForService(catalog.organization, catalog.branch, service);
      state = BookingState(
        step: 1,
        catalog: catalog,
        service: service,
        employees: employees,
      );
    } catch (error) {
      state = BookingState(
        step: 1,
        catalog: catalog,
        service: service,
        error: error,
      );
    }
  }

  void selectEmployee(Employee employee) {
    state = BookingState(
      step: 2,
      catalog: state.catalog,
      service: state.service,
      employees: state.employees,
      employee: employee,
    );
  }

  Future<void> selectDate(DateTime date) async {
    final catalog = state.catalog;
    final service = state.service;
    final employee = state.employee;
    if (catalog == null || service == null || employee == null) return;
    state = BookingState(
      step: 3,
      isLoading: true,
      catalog: catalog,
      service: service,
      employees: state.employees,
      employee: employee,
      date: date,
    );
    try {
      final availability = await ref
          .read(bookingRepositoryProvider)
          .availability(
            branchId: catalog.branch.id,
            employeeId: employee.id,
            serviceId: service.id,
            date: date,
          );
      state = BookingState(
        step: 3,
        catalog: catalog,
        service: service,
        employees: state.employees,
        employee: employee,
        date: date,
        availability: availability,
      );
    } catch (error) {
      state = BookingState(
        step: 3,
        catalog: catalog,
        service: service,
        employees: state.employees,
        employee: employee,
        date: date,
        error: error,
      );
    }
  }

  void selectSlot(AvailabilitySlot slot) {
    state = BookingState(
      step: 4,
      catalog: state.catalog,
      service: state.service,
      employees: state.employees,
      employee: state.employee,
      date: state.date,
      availability: state.availability,
      slot: slot,
    );
  }

  void back() {
    final target = (state.step - 1).clamp(0, 4);
    state = BookingState(
      step: target,
      catalog: state.catalog,
      service: state.service,
      employees: state.employees,
      employee: target >= 2 ? state.employee : null,
      date: target >= 3 ? state.date : null,
      availability: target >= 3 ? state.availability : null,
      slot: target >= 4 ? state.slot : null,
    );
  }

  Future<Appointment?> submit(String? note) async {
    final catalog = state.catalog;
    final service = state.service;
    final employee = state.employee;
    final slot = state.slot;
    if (catalog == null ||
        service == null ||
        employee == null ||
        slot == null) {
      return null;
    }
    final key = state.idempotencyKey ?? const Uuid().v4();
    state = BookingState(
      step: 4,
      isSubmitting: true,
      catalog: catalog,
      service: service,
      employees: state.employees,
      employee: employee,
      date: state.date,
      availability: state.availability,
      slot: slot,
      idempotencyKey: key,
    );
    try {
      final appointment = await ref
          .read(bookingRepositoryProvider)
          .create(
            branchId: catalog.branch.id,
            employeeId: employee.id,
            serviceId: service.id,
            startsAt: slot.start,
            idempotencyKey: key,
            note: note,
          );
      for (final view in const ['all', 'upcoming', 'past', 'cancelled']) {
        ref.invalidate(appointmentsProvider(view));
      }
      ref.invalidate(appointmentDetailProvider(appointment.id));
      state = const BookingState();
      return appointment;
    } catch (error) {
      state = BookingState(
        step: 4,
        catalog: catalog,
        service: service,
        employees: state.employees,
        employee: employee,
        date: state.date,
        availability: state.availability,
        slot: slot,
        idempotencyKey: key,
        error: error,
      );
      return null;
    }
  }

  void reset() => state = const BookingState();
}
