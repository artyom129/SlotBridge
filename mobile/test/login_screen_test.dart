import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/data/auth_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/auth/login_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<AppUser> updateProfile({
    required String firstName,
    required String lastName,
    String? phone,
  }) => throw UnimplementedError();
  @override
  Future<bool> hasSession() async => false;

  @override
  Future<AppUser> login(String email, String password) {
    throw const AppException('Invalid email or password');
  }

  @override
  Future<AppUser> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  }) => throw UnimplementedError();

  @override
  Future<AppUser> currentUser() => throw UnimplementedError();

  @override
  Future<void> logout() async {}
}

void main() {
  testWidgets('login validates input and displays API-safe error', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        ],
        child: const MaterialApp(
          locale: Locale('ru'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: LoginScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('loginButton')));
    await tester.pump();
    expect(find.text('Введите корректную электронную почту'), findsOneWidget);
    expect(find.text('Введите пароль'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('emailField')),
      'client@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('passwordField')),
      'bad-password',
    );
    await tester.tap(find.byKey(const Key('loginButton')));
    await tester.pumpAndSettle();
    expect(find.text('Неверная электронная почта или пароль.'), findsOneWidget);
  });
}
