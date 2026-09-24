import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/core/ui/widgets.dart';
import 'package:slotbridge_mobile/data/review_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/reviews/employee_reviews_screen.dart';
import 'package:slotbridge_mobile/features/reviews/review_form_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _ReviewRepository implements ReviewRepository {
  _ReviewRepository({this.error});
  final Object? error;
  int createCalls = 0;

  static final review = Review(
    id: 'review-1',
    appointmentId: 'appointment-1',
    employeeId: 'employee-1',
    serviceId: 'service-1',
    serviceName: 'Стрижка',
    clientDisplayName: 'Client A.',
    overallRating: 5,
    qualityRating: 5,
    serviceRating: 5,
    punctualityRating: 4,
    comment: 'Отлично',
    isAnonymous: false,
    canEdit: true,
    editDeadline: DateTime.now().add(const Duration(hours: 24)),
    reply: null,
    createdAt: DateTime.now(),
    externalReviewUrl2gis: 'https://2gis.kz/test',
  );

  @override
  Future<Review> create({
    required String appointmentId,
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool isAnonymous = false,
  }) async {
    createCalls++;
    if (error != null) throw error!;
    return review;
  }

  @override
  Future<ReviewPage> employeeReviews(
    String employeeId, {
    int? rating,
    String sort = 'newest',
  }) async => ReviewPage(items: [review], total: 1);

  @override
  Future<EmployeeRating> employeeRating(String employeeId) async =>
      const EmployeeRating(
        employeeId: 'employee-1',
        averageRating: 4.8,
        reviewsCount: 5,
        distribution: {1: 0, 2: 0, 3: 0, 4: 1, 5: 4},
        averageQualityRating: 4.8,
        averageServiceRating: 4.6,
        averagePunctualityRating: 4.4,
      );

  @override
  Future<Review> forAppointment(String appointmentId) async => review;

  @override
  Future<Review> get(String reviewId) async => review;

  @override
  Future<Review> update(
    String reviewId, {
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool? isAnonymous,
  }) async => review;
}

Widget _app(
  Widget home,
  ReviewRepository repository, {
  Locale locale = const Locale('ru'),
}) => ProviderScope(
  overrides: [reviewRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    locale: locale,
    theme: ThemeData.light(useMaterial3: true),
    darkTheme: ThemeData.dark(useMaterial3: true),
    themeMode: ThemeMode.dark,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: home,
  ),
);

void main() {
  setUpAll(() async {
    await initializeDateFormatting('en');
    await initializeDateFormatting('ru');
  });

  testWidgets('completed appointment card exposes working review CTA', (
    tester,
  ) async {
    var tapped = false;
    final start = DateTime(2026, 1, 1, 10);
    final appointment = Appointment(
      id: 'appointment-1',
      organizationId: 'organization-1',
      branch: const ResourceSummary(id: 'branch-1', name: 'Main'),
      employee: const ResourceSummary(id: 'employee-1', name: 'Алекс'),
      service: const ResourceSummary(id: 'service-1', name: 'Стрижка'),
      startsAt: start.toUtc(),
      endsAt: start.add(const Duration(hours: 1)).toUtc(),
      localStartsAt: start,
      localEndsAt: start.add(const Duration(hours: 1)),
      timezone: 'UTC',
      status: 'COMPLETED',
      clientNote: null,
      cancellationReason: null,
      cancelledAt: null,
      history: const [],
    );
    await tester.pumpWidget(
      _app(
        Scaffold(
          body: AppointmentCard(
            appointment: appointment,
            onTap: () {},
            reviewActionLabel: 'Оставить отзыв',
            onReview: () => tapped = true,
          ),
        ),
        _ReviewRepository(),
      ),
    );
    await tester.tap(find.text('Оставить отзыв'));
    expect(tapped, isTrue);
  });

  testWidgets(
    'completed appointment review form publishes once and shows success',
    (tester) async {
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repository = _ReviewRepository();
      await tester.pumpWidget(
        _app(
          const ReviewFormScreen(appointmentId: 'appointment-1'),
          repository,
        ),
      );

      await tester.ensureVisible(find.byKey(const Key('reviewStar5')));
      await tester.tap(find.byKey(const Key('reviewStar5')));
      await tester.pump();
      await tester.ensureVisible(find.byKey(const Key('publishReviewButton')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('publishReviewButton')));
      await tester.pumpAndSettle();

      expect(repository.createCalls, 1);
      expect(find.text('Отзыв опубликован'), findsOneWidget);
      expect(find.text('Открыть 2GIS'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'review error remains actionable and does not show false success',
    (tester) async {
      final repository = _ReviewRepository(
        error: const AppException(
          'Already exists',
          code: 'REVIEW_ALREADY_EXISTS',
          statusCode: 409,
        ),
      );
      await tester.pumpWidget(
        _app(
          const ReviewFormScreen(appointmentId: 'appointment-1'),
          repository,
          locale: const Locale('en'),
        ),
      );
      await tester.ensureVisible(find.byKey(const Key('reviewStar4')));
      await tester.tap(find.byKey(const Key('reviewStar4')));
      await tester.pump();
      await tester.ensureVisible(find.byKey(const Key('publishReviewButton')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('publishReviewButton')));
      await tester.pumpAndSettle();

      expect(
        find.text('You have already reviewed this appointment.'),
        findsOneWidget,
      );
      expect(find.text('Review published'), findsNothing);
    },
  );

  testWidgets('employee reviews render aggregate, filters, and review card', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        const EmployeeReviewsScreen(
          employeeId: 'employee-1',
          employeeName: 'Алекс',
        ),
        _ReviewRepository(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('4.8'), findsOneWidget);
    expect(find.text('Отзывов: 5'), findsOneWidget);
    expect(find.text('Client A.'), findsOneWidget);
    expect(find.text('Отлично'), findsOneWidget);
    expect(find.text('Все оценки'), findsOneWidget);
  });
}
