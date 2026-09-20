import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/data/auth_repository.dart';
import 'package:slotbridge_mobile/domain/models.dart';
import 'package:slotbridge_mobile/features/profile/profile_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _ProfileRepository implements AuthRepository {
  static const user = AppUser(
    id: 'client-1',
    email: 'very.long.client.email@example.com',
    firstName: 'Александр',
    lastName: 'Пользователь',
    role: 'CLIENT',
    phone: '+7 777 123 45 67',
  );

  @override
  Future<bool> hasSession() async => true;

  @override
  Future<AppUser> currentUser() async => user;

  @override
  Future<AppUser> updateProfile({
    required String firstName,
    required String lastName,
    String? phone,
  }) async => AppUser(
    id: user.id,
    email: user.email,
    firstName: firstName,
    lastName: lastName,
    role: user.role,
    phone: phone,
  );

  @override
  Future<void> logout() async {}

  @override
  Future<AppUser> login(String email, String password) =>
      throw UnimplementedError();

  @override
  Future<AppUser> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  }) => throw UnimplementedError();
}

void main() {
  testWidgets('edit profile dialog fits a small dark screen', (tester) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authRepositoryProvider.overrideWithValue(_ProfileRepository()),
        ],
        child: MaterialApp(
          locale: const Locale('ru'),
          theme: ThemeData.light(useMaterial3: true),
          darkTheme: ThemeData.dark(useMaterial3: true),
          themeMode: ThemeMode.dark,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: const ProfileScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Редактировать профиль').first);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('editProfileDialog')), findsOneWidget);
    expect(find.byKey(const Key('editProfileFirstName')), findsOneWidget);
    expect(find.byKey(const Key('editProfileLastName')), findsOneWidget);
    expect(find.byKey(const Key('editProfilePhone')), findsOneWidget);
    expect(find.byKey(const Key('editProfileEmail')), findsOneWidget);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('editProfileEmail')))
          .readOnly,
      isTrue,
    );

    await tester.ensureVisible(find.byKey(const Key('editProfileSaveButton')));
    expect(find.byKey(const Key('editProfileBackButton')), findsOneWidget);
    expect(find.byKey(const Key('editProfileSaveButton')), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.tap(find.byKey(const Key('editProfileFirstName')));
    await tester.enterText(
      find.byKey(const Key('editProfileFirstName')),
      'Новое имя',
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
