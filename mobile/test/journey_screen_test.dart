import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/data/catalog_repository.dart';
import 'package:slotbridge_mobile/data/journey_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/journey/journey_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _CatalogRepository implements CatalogRepository {
  _CatalogRepository(this.catalog);

  final CatalogBootstrap catalog;

  @override
  Future<CatalogBootstrap> loadBootstrap() async => catalog;

  @override
  Future<List<Employee>> employeesForService(
    Organization organization,
    Branch branch,
    Service service,
  ) async => const [];
}

class _JourneyRepository implements JourneyRepository {
  _JourneyRepository(this.plans);

  final List<Future<JourneyPlan> Function()> plans;
  int calls = 0;

  @override
  Future<JourneyPlan> plan({
    required String branchId,
    required List<String> serviceIds,
    required DateTime date,
    required TimeOfDayValue after,
    required TimeOfDayValue before,
  }) {
    final result = plans[calls.clamp(0, plans.length - 1)];
    calls++;
    return result();
  }

  @override
  Future<List<Appointment>> book({
    required String branchId,
    required JourneyRoute route,
    required String idempotencyKey,
  }) async => const [];
}

CatalogBootstrap _catalog() => CatalogBootstrap(
  organization: const Organization(
    id: 'org',
    name: 'SlotBridge',
    timezone: 'UTC',
    isActive: true,
  ),
  branch: const Branch(
    id: 'branch',
    organizationId: 'org',
    name: 'Center',
    address: 'Address',
    timezone: 'UTC',
    isActive: true,
  ),
  services: const [
    Service(
      id: 'service-1',
      organizationId: 'org',
      name: 'Очень длинное название первой услуги',
      description: 'Description',
      durationMinutes: 30,
      price: null,
      isActive: true,
    ),
    Service(
      id: 'service-2',
      organizationId: 'org',
      name: 'Консультация',
      description: 'Description',
      durationMinutes: 30,
      price: null,
      isActive: true,
    ),
  ],
);

JourneyPlan _plan() {
  final firstStart = DateTime.utc(2099, 1, 5, 16);
  final firstEnd = DateTime.utc(2099, 1, 5, 16, 30);
  final secondStart = DateTime.utc(2099, 1, 5, 16, 35);
  final secondEnd = DateTime.utc(2099, 1, 5, 17, 5);
  JourneyRoute route(String strategy) => JourneyRoute(
    strategy: strategy,
    steps: [
      JourneyStep(
        service: const ResourceSummary(
          id: 'service-1',
          name: 'Очень длинное название первой услуги',
        ),
        employee: const ResourceSummary(
          id: 'employee-1',
          name: 'Очень длинное имя специалиста',
        ),
        startsAt: firstStart,
        endsAt: firstEnd,
        localStartsAt: firstStart,
        localEndsAt: firstEnd,
      ),
      JourneyStep(
        service: const ResourceSummary(id: 'service-2', name: 'Консультация'),
        employee: const ResourceSummary(id: 'employee-2', name: 'Мария'),
        startsAt: secondStart,
        endsAt: secondEnd,
        localStartsAt: secondStart,
        localEndsAt: secondEnd,
      ),
    ],
    startsAt: firstStart,
    endsAt: secondEnd,
    totalMinutes: 65,
    waitMinutes: 5,
    employeeCount: 2,
  );
  return JourneyPlan(
    timezone: 'UTC',
    routes: [route('FASTEST'), route('EARLIEST'), route('FEWEST_EMPLOYEES')],
  );
}

Widget _app(_JourneyRepository journey, {bool dark = false}) => ProviderScope(
  overrides: [
    catalogRepositoryProvider.overrideWithValue(_CatalogRepository(_catalog())),
    journeyRepositoryProvider.overrideWithValue(journey),
  ],
  child: MaterialApp(
    locale: const Locale('ru'),
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    theme: ThemeData.light(useMaterial3: true),
    darkTheme: ThemeData.dark(useMaterial3: true),
    themeMode: dark ? ThemeMode.dark : ThemeMode.light,
    home: const JourneyScreen(),
  ),
);

Future<void> _selectAndPlan(WidgetTester tester) async {
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const ValueKey('journey-service-service-1')));
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('journey-service-service-2')));
  await tester.pump();
  await tester.ensureVisible(find.byKey(const Key('planJourneyButton')));
  await tester.tap(find.byKey(const Key('planJourneyButton')));
}

void main() {
  testWidgets('renders three journey strategies on a small dark screen', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repository = _JourneyRepository([() async => _plan()]);

    await tester.pumpWidget(_app(repository, dark: true));
    await _selectAndPlan(tester);
    await tester.pumpAndSettle();

    expect(find.text('Быстрее всего'), findsOneWidget);
    expect(find.text('Как можно раньше'), findsOneWidget);
    expect(find.text('Меньше сотрудников'), findsOneWidget);
    expect(find.text('Ожидание: 5 мин'), findsNWidgets(3));
    expect(tester.takeException(), isNull);
  });

  testWidgets('keeps plan disabled while loading and retries after error', (
    tester,
  ) async {
    final pending = Completer<JourneyPlan>();
    final repository = _JourneyRepository([
      () => pending.future,
      () async => throw const AppException('Offline', code: 'connection_error'),
      () async => _plan(),
    ]);
    await tester.pumpWidget(_app(repository));
    await _selectAndPlan(tester);
    await tester.pump();

    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('planJourneyButton')))
          .onPressed,
      isNull,
    );
    pending.complete(_plan());
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('planJourneyButton')));
    await tester.tap(find.byKey(const Key('planJourneyButton')));
    await tester.pumpAndSettle();
    expect(find.text('Повторить'), findsOneWidget);

    await tester.tap(find.text('Повторить'));
    await tester.pumpAndSettle();
    expect(repository.calls, 3);
    expect(find.text('Быстрее всего'), findsOneWidget);
  });
}
