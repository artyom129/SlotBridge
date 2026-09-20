import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../core/errors/app_exception.dart';
import '../../core/providers.dart';
import '../../data/journey_repository.dart';
import '../../domain/models.dart';
import '../appointments/appointment_providers.dart';

final journeyControllerProvider =
    NotifierProvider<JourneyController, JourneyState>(JourneyController.new);

class JourneyState {
  const JourneyState({
    this.loading = false,
    this.submitting = false,
    this.catalog,
    this.selectedServices = const [],
    this.date,
    this.after = const TimeOfDayValue(9, 0),
    this.before = const TimeOfDayValue(18, 0),
    this.plan,
    this.error,
    this.conflict = false,
    this.idempotencyKey,
  });

  final bool loading;
  final bool submitting;
  final CatalogBootstrap? catalog;
  final List<Service> selectedServices;
  final DateTime? date;
  final TimeOfDayValue after;
  final TimeOfDayValue before;
  final JourneyPlan? plan;
  final Object? error;
  final bool conflict;
  final String? idempotencyKey;

  JourneyState copyWith({
    bool? loading,
    bool? submitting,
    CatalogBootstrap? catalog,
    List<Service>? selectedServices,
    DateTime? date,
    TimeOfDayValue? after,
    TimeOfDayValue? before,
    JourneyPlan? plan,
    Object? error,
    bool clearError = false,
    bool? conflict,
    String? idempotencyKey,
    bool clearPlan = false,
  }) => JourneyState(
    loading: loading ?? this.loading,
    submitting: submitting ?? this.submitting,
    catalog: catalog ?? this.catalog,
    selectedServices: selectedServices ?? this.selectedServices,
    date: date ?? this.date,
    after: after ?? this.after,
    before: before ?? this.before,
    plan: clearPlan ? null : plan ?? this.plan,
    error: clearError ? null : error ?? this.error,
    conflict: conflict ?? this.conflict,
    idempotencyKey: idempotencyKey ?? this.idempotencyKey,
  );
}

class JourneyController extends Notifier<JourneyState> {
  int _requestSerial = 0;

  @override
  JourneyState build() => const JourneyState();

  Future<void> load() async {
    if (state.catalog != null || state.loading) return;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final catalog = await ref.read(catalogRepositoryProvider).loadBootstrap();
      state = state.copyWith(
        loading: false,
        catalog: catalog,
        date: DateTime.now().add(const Duration(days: 1)),
      );
    } catch (error) {
      state = state.copyWith(loading: false, error: error);
    }
  }

  void toggleService(Service service) {
    if (state.loading || state.submitting) return;
    final selected = [...state.selectedServices];
    final index = selected.indexWhere((item) => item.id == service.id);
    if (index >= 0) {
      selected.removeAt(index);
    } else if (selected.length < 6) {
      selected.add(service);
    }
    state = state.copyWith(
      selectedServices: selected,
      clearPlan: true,
      clearError: true,
      conflict: false,
      idempotencyKey: const Uuid().v4(),
    );
  }

  void setDate(DateTime value) {
    state = state.copyWith(
      date: value,
      clearPlan: true,
      clearError: true,
      conflict: false,
    );
  }

  void setTimes(TimeOfDayValue after, TimeOfDayValue before) {
    state = state.copyWith(
      after: after,
      before: before,
      clearPlan: true,
      clearError: true,
      conflict: false,
    );
  }

  Future<void> plan({bool afterConflict = false}) async {
    final catalog = state.catalog;
    final date = state.date;
    if (state.loading ||
        state.submitting ||
        catalog == null ||
        date == null ||
        state.selectedServices.length < 2) {
      return;
    }
    final serial = ++_requestSerial;
    state = state.copyWith(
      loading: true,
      clearError: true,
      clearPlan: true,
      conflict: afterConflict,
    );
    try {
      final result = await ref
          .read(journeyRepositoryProvider)
          .plan(
            branchId: catalog.branch.id,
            serviceIds: state.selectedServices.map((item) => item.id).toList(),
            date: date,
            after: state.after,
            before: state.before,
          );
      if (serial != _requestSerial) return;
      state = state.copyWith(
        loading: false,
        plan: result,
        conflict: afterConflict,
        idempotencyKey: const Uuid().v4(),
      );
    } catch (error) {
      if (serial != _requestSerial) return;
      state = state.copyWith(
        loading: false,
        error: error,
        conflict: false,
        clearPlan: true,
      );
    }
  }

  Future<List<Appointment>?> book(JourneyRoute route) async {
    final catalog = state.catalog;
    if (catalog == null || state.submitting) return null;
    final key = state.idempotencyKey ?? const Uuid().v4();
    state = state.copyWith(
      submitting: true,
      idempotencyKey: key,
      clearError: true,
      conflict: false,
    );
    try {
      final appointments = await ref
          .read(journeyRepositoryProvider)
          .book(branchId: catalog.branch.id, route: route, idempotencyKey: key);
      for (final view in const ['all', 'upcoming', 'past', 'cancelled']) {
        ref.invalidate(appointmentsProvider(view));
      }
      state = state.copyWith(submitting: false);
      return appointments;
    } catch (error) {
      state = state.copyWith(submitting: false, error: error);
      if (error is AppException && error.code == 'JOURNEY_CONFLICT') {
        await plan(afterConflict: true);
      }
      return null;
    }
  }

  void reset() {
    _requestSerial++;
    state = const JourneyState();
  }
}
