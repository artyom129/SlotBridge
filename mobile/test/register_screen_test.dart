import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/app.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/data/auth_repository.dart';
import 'package:slotbridge_mobile/data/booking_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/auth/login_screen.dart';
import 'package:slotbridge_mobile/features/auth/register_screen.dart';
import 'package:slotbridge_mobile/features/home/home_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _FakeAuthRepository implements AuthRepository {
  _FakeAuthRepository({this.registerError});

  final Object? registerError;
  int registerCalls = 0;
  int currentUserCalls = 0;
  String? registeredEmail;
  bool sessionAvailable = false;

  static const user = AppUser(
    id: 'user-1',
    email: 'new.client@example.com',
    firstName: 'Анна',
    lastName: 'Смирнова',
    role: 'CLIENT',
  );

  @override
  Future<bool> hasSession() async => sessionAvailable;

  @override
  Future<AppUser> login(String email, String password) async {
    sessionAvailable = true;
    return user;
  }

  @override
  Future<AppUser> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  }) async {
    registerCalls += 1;
    registeredEmail = email;
    if (registerError != null) throw registerError!;
    sessionAvailable = true;
    return user;
  }

  @override
  Future<AppUser> currentUser() async {
    currentUserCalls += 1;
    return user;
  }

  @override
  Future<void> logout() async => sessionAvailable = false;
}

class _FakeBookingRepository implements BookingRepository {
  @override
  Future<List<Appointment>> list({String view = 'all'}) async => const [];

  @override
  Future<Availability> availability({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime date,
  }) => throw UnimplementedError();

  @override
  Future<Appointment> cancel(String id, {String? reason}) =>
      throw UnimplementedError();

  @override
  Future<Appointment> create({
    required String branchId,
    required String employeeId,
    required String serviceId,
    required DateTime startsAt,
    required String idempotencyKey,
    String? note,
  }) => throw UnimplementedError();

  @override
  Future<Appointment> detail(String id) => throw UnimplementedError();

  @override
  Future<Appointment> reschedule(
    String id, {
    required DateTime startsAt,
    String? reason,
  }) => throw UnimplementedError();
}

Future<void> _pumpRegister(
  WidgetTester tester,
  _FakeAuthRepository repository,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repository)],
      child: const MaterialApp(
        locale: Locale('ru'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: RegisterScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _fillValidForm(WidgetTester tester) async {
  await tester.enterText(
    find.byKey(const Key('registerFirstNameField')),
    'Анна',
  );
  await tester.enterText(
    find.byKey(const Key('registerLastNameField')),
    'Смирнова',
  );
  await tester.enterText(
    find.byKey(const Key('registerEmailField')),
    'new.client@example.com',
  );
  await tester.enterText(
    find.byKey(const Key('registerPasswordField')),
    'StrongPass123!',
  );
  await tester.enterText(
    find.byKey(const Key('registerConfirmPasswordField')),
    'StrongPass123!',
  );
}

Future<void> _tapRegister(WidgetTester tester) async {
  final button = find.byKey(const Key('registerButton'));
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('navigates from login to register and back', (tester) async {
    final repository = _FakeAuthRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(repository)],
        child: const SlotBridgeApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);

    final registerLink = find.byKey(const Key('loginRegisterLink'));
    await tester.ensureVisible(registerLink);
    await tester.tap(registerLink);
    await tester.pumpAndSettle();
    expect(find.byType(RegisterScreen), findsOneWidget);

    final loginLink = find.byKey(const Key('registerLoginLink'));
    await tester.ensureVisible(loginLink);
    await tester.tap(loginLink);
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
  });

  testWidgets('validates required registration fields', (tester) async {
    await _pumpRegister(tester, _FakeAuthRepository());
    await _tapRegister(tester);

    expect(find.text('Введите имя'), findsOneWidget);
    expect(find.text('Введите фамилию'), findsOneWidget);
    expect(find.text('Введите электронную почту'), findsOneWidget);
    expect(find.text('Введите пароль'), findsOneWidget);
    expect(find.text('Повторите пароль'), findsOneWidget);
  });

  testWidgets('validates email and matching passwords', (tester) async {
    await _pumpRegister(tester, _FakeAuthRepository());
    await tester.enterText(
      find.byKey(const Key('registerFirstNameField')),
      'Анна',
    );
    await tester.enterText(
      find.byKey(const Key('registerLastNameField')),
      'Смирнова',
    );
    await tester.enterText(
      find.byKey(const Key('registerEmailField')),
      'wrong-email',
    );
    await tester.enterText(
      find.byKey(const Key('registerPasswordField')),
      'StrongPass123!',
    );
    await tester.enterText(
      find.byKey(const Key('registerConfirmPasswordField')),
      'DifferentPass123!',
    );
    await _tapRegister(tester);

    expect(find.text('Введите корректную электронную почту'), findsOneWidget);
    expect(find.text('Пароли не совпадают'), findsOneWidget);
  });

  testWidgets('submits a valid registration', (tester) async {
    final repository = _FakeAuthRepository();
    await _pumpRegister(tester, repository);
    await _fillValidForm(tester);
    await _tapRegister(tester);

    expect(repository.registerCalls, 1);
    expect(repository.registeredEmail, 'new.client@example.com');
    expect(find.byKey(const Key('registerError')), findsNothing);
  });

  testWidgets('successful registration opens home and restores the session', (
    tester,
  ) async {
    final repository = _FakeAuthRepository();
    final bookingRepository = _FakeBookingRepository();

    Widget app() => ProviderScope(
      overrides: [
        authRepositoryProvider.overrideWithValue(repository),
        bookingRepositoryProvider.overrideWithValue(bookingRepository),
      ],
      child: const SlotBridgeApp(),
    );

    await tester.pumpWidget(app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('loginRegisterLink')));
    await tester.pumpAndSettle();
    await _fillValidForm(tester);
    await _tapRegister(tester);

    expect(find.byType(HomeScreen), findsOneWidget);
    expect(repository.sessionAvailable, isTrue);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    await tester.pumpWidget(app());
    await tester.pumpAndSettle();

    expect(find.byType(HomeScreen), findsOneWidget);
    expect(repository.currentUserCalls, 1);
  });

  testWidgets('shows duplicate email error in Russian', (tester) async {
    final repository = _FakeAuthRepository(
      registerError: const AppException(
        'Email already registered',
        statusCode: 409,
      ),
    );
    await _pumpRegister(tester, repository);
    await _fillValidForm(tester);
    await _tapRegister(tester);

    expect(find.text('Эта электронная почта уже используется'), findsOneWidget);
  });

  testWidgets('returns to login when registration succeeds but login fails', (
    tester,
  ) async {
    final repository = _FakeAuthRepository(
      registerError: const AppException(
        'Аккаунт создан. Теперь войдите.',
        code: 'registration_login_failed',
      ),
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(repository)],
        child: const SlotBridgeApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('loginRegisterLink')));
    await tester.pumpAndSettle();
    await _fillValidForm(tester);
    await _tapRegister(tester);

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.text('Аккаунт создан. Теперь войдите.'), findsOneWidget);
  });
}
