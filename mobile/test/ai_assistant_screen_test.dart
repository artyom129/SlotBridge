import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';
import 'package:slotbridge_mobile/core/network/api_client.dart';
import 'package:slotbridge_mobile/core/providers.dart';
import 'package:slotbridge_mobile/core/storage/token_storage.dart';
import 'package:slotbridge_mobile/features/ai/ai_assistant_screen.dart';
import 'package:slotbridge_mobile/l10n/app_localizations.dart';

class _MemoryTokenStorage implements TokenStorage {
  @override
  Future<void> clear() async {}
  @override
  Future<String?> read() async => 'test-token';
  @override
  Future<void> write(String value) async {}
}

class _FakeApiClient extends ApiClient {
  _FakeApiClient(this.handlers) : super(_MemoryTokenStorage());
  final List<Future<dynamic> Function()> handlers;
  int calls = 0;
  final payloads = <Object?>[];

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? headers,
  }) {
    payloads.add(data);
    return handlers[calls++]();
  }
}

Widget _app(_FakeApiClient api, {bool dark = false}) => ProviderScope(
  overrides: [apiClientProvider.overrideWithValue(api)],
  child: MaterialApp(
    locale: const Locale('ru'),
    theme: ThemeData.light(useMaterial3: true),
    darkTheme: ThemeData.dark(useMaterial3: true),
    themeMode: dark ? ThemeMode.dark : ThemeMode.light,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    home: const AiAssistantScreen(),
  ),
);

void main() {
  testWidgets(
    'disables duplicate actions and fits confirmation on small screen',
    (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final response = Completer<dynamic>();
      final api = _FakeApiClient([() => response.future]);
      await tester.pumpWidget(_app(api));
      await tester.tap(find.byKey(const Key('aiQuickAction-0')));
      await tester.pump();

      expect(api.calls, 1);
      expect(
        tester
            .widget<OutlinedButton>(find.byKey(const Key('aiQuickAction-0')))
            .onPressed,
        isNull,
      );
      expect(
        tester
            .widget<IconButton>(find.byKey(const Key('aiSendButton')))
            .onPressed,
        isNull,
      );
      expect(api.calls, 1);

      response.complete({
        'text':
            'Найден вариант с очень длинным описанием, которое переносится.',
        'state': <String, dynamic>{},
        'items': [
          {
            'name': 'Очень длинное название услуги для маленького экрана',
            'employee': 'Очень длинное имя сотрудника для переноса',
          },
        ],
        'confirmation_token': 'confirmation-token',
      });
      await tester.pumpAndSettle();

      expect(find.text('Нужно подтверждение'), findsOneWidget);
      expect(find.byKey(const Key('aiConfirmButton')), findsOneWidget);
      expect(
        find.byKey(const Key('aiCancelConfirmationButton')),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('retry does not duplicate the user message', (tester) async {
    final api = _FakeApiClient([
      () async => throw Exception('temporary failure'),
      () async => {
        'text': 'Ответ получен.',
        'state': <String, dynamic>{},
        'items': <dynamic>[],
      },
    ]);
    await tester.pumpWidget(_app(api));
    await tester.enterText(
      find.byKey(const Key('aiMessageInput')),
      'Найди время',
    );
    await tester.tap(find.byKey(const Key('aiSendButton')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('aiRetryButton')), findsOneWidget);
    expect(find.text('Найди время'), findsOneWidget);
    await tester.tap(find.byKey(const Key('aiRetryButton')));
    await tester.pumpAndSettle();

    expect(api.calls, 2);
    expect(find.text('Найди время'), findsOneWidget);
    expect(find.text('Ответ получен.'), findsOneWidget);
    expect(find.byKey(const Key('aiRetryButton')), findsNothing);
  });

  testWidgets('all quick actions are tappable on a small dark screen', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final api = _FakeApiClient(
      List.generate(
        5,
        (_) =>
            () async => {
              'text': 'Готово.',
              'state': <String, dynamic>{},
              'items': <dynamic>[],
            },
      ),
    );
    await tester.pumpWidget(_app(api, dark: true));

    const expected = [
      'Найти время',
      'Записаться',
      'Мои записи',
      'Перенести запись',
      'Лучший слот',
    ];
    for (var index = 0; index < expected.length; index++) {
      final button = find.byKey(Key('aiQuickAction-$index'));
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
      expect(api.calls, index + 1);
    }

    expect(
      api.payloads
          .map((value) => (value! as Map<String, dynamic>)['message'])
          .toList(),
      expected,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('temporary AI failure retries and keeps quick actions usable', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => throw const AppException(
        'Temporary',
        code: 'AI_UNAVAILABLE',
        statusCode: 503,
      ),
      () async => {
        'text': 'Ответ после повтора.',
        'state': <String, dynamic>{},
        'items': <dynamic>[],
      },
      () async => throw Exception('temporary failure'),
      () async => {
        'text': 'Кнопка снова работает.',
        'state': <String, dynamic>{},
        'items': <dynamic>[],
      },
    ]);
    await tester.pumpWidget(_app(api, dark: true));

    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();
    expect(find.text('Ответ после повтора.'), findsOneWidget);
    expect(api.calls, 2);

    await tester.ensureVisible(find.byKey(const Key('aiQuickAction-1')));
    await tester.tap(find.byKey(const Key('aiQuickAction-1')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('aiRetryButton')), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('aiQuickAction-2')));
    await tester.tap(find.byKey(const Key('aiQuickAction-2')));
    await tester.pumpAndSettle();
    expect(find.text('Кнопка снова работает.'), findsOneWidget);
    expect(api.calls, 4);
  });
}
