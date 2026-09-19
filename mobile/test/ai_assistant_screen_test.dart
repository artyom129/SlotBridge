import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
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

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? headers,
  }) {
    return handlers[calls++]();
  }
}

Widget _app(_FakeApiClient api) => ProviderScope(
  overrides: [apiClientProvider.overrideWithValue(api)],
  child: const MaterialApp(
    locale: Locale('ru'),
    localizationsDelegates: [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    home: AiAssistantScreen(),
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
}
