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
  final paths = <String>[];

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? headers,
  }) {
    paths.add(path);
    payloads.add(data);
    return handlers[calls++]();
  }
}

Widget _app(
  _FakeApiClient api, {
  bool dark = false,
  Locale locale = const Locale('ru'),
}) => ProviderScope(
  overrides: [apiClientProvider.overrideWithValue(api)],
  child: MaterialApp(
    locale: locale,
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
  test('classifies AI failures without collapsing their cause', () {
    expect(
      classifyAiFailure(
        const AppException(
          'Timeout',
          code: 'AI_GEMINI_TIMEOUT',
          statusCode: 504,
        ),
      ),
      AiFailureKind.timeout,
    );
    expect(
      classifyAiFailure(
        const AppException('Offline', code: 'connection_error'),
      ),
      AiFailureKind.backendUnavailable,
    );
    expect(
      classifyAiFailure(
        const AppException(
          'Provider',
          code: 'AI_GEMINI_RATE_LIMIT',
          statusCode: 503,
        ),
      ),
      AiFailureKind.rateLimited,
    );
    expect(
      classifyAiFailure(const AppException('Unauthorized', statusCode: 401)),
      AiFailureKind.auth,
    );
    expect(
      classifyAiFailure(const FormatException('bad response')),
      AiFailureKind.invalidResponse,
    );
  });

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

  testWidgets('shows distinct RU Gemini and EN invalid-response errors', (
    tester,
  ) async {
    final ruApi = _FakeApiClient([
      () async => throw const AppException(
        'Provider auth',
        code: 'AI_GEMINI_AUTH',
        statusCode: 503,
      ),
    ]);
    await tester.pumpWidget(_app(ruApi));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();
    expect(
      find.text(
        'Gemini временно недоступен. Обычная запись продолжает работать.',
      ),
      findsOneWidget,
    );

    final enApi = _FakeApiClient([() async => 'not-a-map']);
    await tester.pumpWidget(_app(enApi, locale: const Locale('en')));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();
    expect(
      find.text('AI returned an invalid response. Please try again.'),
      findsOneWidget,
    );
  });

  testWidgets('auth error is not retried or shown as Gemini outage', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => throw const AppException(
        'Unauthorized',
        code: 'token_invalid',
        statusCode: 401,
      ),
    ]);
    await tester.pumpWidget(_app(api));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();

    expect(api.calls, 1);
    expect(
      find.text(
        'Сессия истекла. Войдите снова, чтобы использовать SlotBridge AI.',
      ),
      findsOneWidget,
    );
    expect(find.byKey(const Key('aiRetryButton')), findsNothing);
  });

  testWidgets('rate limit is not amplified by an immediate client retry', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => throw const AppException(
        'Rate limited',
        code: 'AI_GEMINI_RATE_LIMIT',
        statusCode: 503,
      ),
    ]);
    await tester.pumpWidget(_app(api));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();

    expect(api.calls, 1);
    expect(
      find.text(
        'Gemini получил слишком много запросов. '
        'Подождите немного и повторите.',
      ),
      findsOneWidget,
    );
    expect(find.byKey(const Key('aiRetryButton')), findsOneWidget);
    expect(
      tester
          .widget<OutlinedButton>(find.byKey(const Key('aiQuickAction-1')))
          .onPressed,
      isNotNull,
    );
  });

  testWidgets('multi-service journey card fits a small dark screen', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = _FakeApiClient([
      () async => {
        'text': 'Нашёл варианты маршрута',
        'state': <String, dynamic>{'intent': 'MULTI_SERVICE_JOURNEY'},
        'items': [
          {
            'strategy': 'FASTEST',
            'total_minutes': 95,
            'wait_minutes': 5,
            'employee_count': 2,
            'steps': [
              {
                'time': '16:00–16:40',
                'service': 'Очень длинное название услуги для проверки',
                'employee': 'Очень длинное имя сотрудника',
              },
              {
                'time': '16:45–17:35',
                'service': 'Консультация',
                'employee': 'Мария',
              },
            ],
          },
        ],
      },
    ]);
    await tester.pumpWidget(_app(api, dark: true));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();

    expect(find.text('Быстрее всего'), findsOneWidget);
    expect(find.text('Ожидание: 5 мин'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('service employee and slot cards send structured selections', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => {
        'text': 'Выберите услугу',
        'state': <String, dynamic>{},
        'items': [
          {
            'type': 'service',
            'value': 'Стрижка',
            'name': 'Стрижка',
            'duration_minutes': 45,
          },
        ],
      },
      () async => {
        'text': 'Выберите сотрудника',
        'state': <String, dynamic>{'service': 'Стрижка'},
        'items': [
          {'type': 'employee', 'value': 'Алекс', 'name': 'Алекс'},
        ],
      },
      () async => {
        'text': 'Выберите время',
        'state': <String, dynamic>{
          'service': 'Стрижка',
          'employee': 'Алекс',
          'date': '2099-01-05',
          'candidate_slots': ['17:30'],
        },
        'items': [
          {'type': 'slot', 'value': '17:30', 'time': '17:30'},
        ],
      },
      () async => {
        'text': 'Подтвердите действие',
        'state': <String, dynamic>{
          'pending_action': 'CREATE_BOOKING',
          'service': 'Стрижка',
          'employee': 'Алекс',
          'date': '2099-01-05',
          'time': '17:30',
        },
        'items': <dynamic>[],
        'confirmation_token': 'booking-confirmation',
      },
    ]);
    await tester.pumpWidget(_app(api, dark: true));

    await tester.tap(find.byKey(const Key('aiQuickAction-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiResult-service-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiResult-employee-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiResult-slot-0')));
    await tester.pumpAndSettle();

    expect(api.calls, 4);
    expect((api.payloads[1] as Map<String, dynamic>)['selection'], {
      'type': 'service',
      'value': 'Стрижка',
      'label': 'Стрижка',
    });
    expect(
      (api.payloads[1] as Map<String, dynamic>)['state'],
      containsPair('service', 'Стрижка'),
    );
    expect((api.payloads[2] as Map<String, dynamic>)['selection'], {
      'type': 'employee',
      'value': 'Алекс',
      'label': 'Алекс',
    });
    expect(
      (api.payloads[2] as Map<String, dynamic>)['state'],
      allOf(
        containsPair('service', 'Стрижка'),
        containsPair('employee', 'Алекс'),
      ),
    );
    expect((api.payloads[3] as Map<String, dynamic>)['selection'], {
      'type': 'slot',
      'value': '17:30',
      'label': '17:30',
    });
    expect(
      (api.payloads[3] as Map<String, dynamic>)['state'],
      containsPair('time', '17:30'),
    );
    expect(find.text('Нужно подтверждение'), findsOneWidget);
    expect(api.paths.where((path) => path == '/ai/confirm'), isEmpty);
  });

  testWidgets('appointment and journey cards send their structured action', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => {
        'text': 'Ваши записи',
        'state': <String, dynamic>{'intent': 'CANCEL'},
        'items': [
          {
            'type': 'appointment',
            'value': '2099-01-05T17:30:00+00:00',
            'service': 'Стрижка',
            'employee': 'Алекс',
            'starts_at': '2099-01-05T17:30:00+00:00',
          },
        ],
      },
      () async => {
        'text': 'Выбрана запись',
        'state': <String, dynamic>{'selected_appointment': 'Стрижка'},
        'items': <dynamic>[],
      },
      () async => {
        'text': 'Маршруты',
        'state': <String, dynamic>{'intent': 'MULTI_SERVICE_JOURNEY'},
        'items': [
          {
            'type': 'journey',
            'value': 'FASTEST',
            'strategy': 'FASTEST',
            'total_minutes': 60,
            'wait_minutes': 0,
            'steps': [
              {
                'time': '17:30–18:00',
                'service': 'Стрижка',
                'employee': 'Алекс',
              },
            ],
          },
        ],
      },
      () async => {
        'text': 'Маршрут выбран',
        'state': <String, dynamic>{'selected_journey': 'FASTEST'},
        'items': <dynamic>[],
      },
    ]);
    await tester.pumpWidget(_app(api));

    await tester.tap(find.byKey(const Key('aiQuickAction-2')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiResult-appointment-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiQuickAction-4')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('aiResult-journey-0')));
    await tester.pumpAndSettle();

    expect((api.payloads[1] as Map<String, dynamic>)['selection'], {
      'type': 'appointment',
      'value': '2099-01-05T17:30:00+00:00',
      'label': 'Стрижка · 2099-01-05T17:30:00+00:00',
    });
    expect(
      (api.payloads[1] as Map<String, dynamic>)['state'],
      containsPair(
        'selected_appointment',
        'Стрижка · 2099-01-05T17:30:00+00:00',
      ),
    );
    expect((api.payloads[3] as Map<String, dynamic>)['selection'], {
      'type': 'journey',
      'value': 'FASTEST',
      'label': 'FASTEST',
    });
    expect(
      (api.payloads[3] as Map<String, dynamic>)['state'],
      containsPair('selected_journey', 'FASTEST'),
    );
  });

  testWidgets('result card blocks repeated taps while selection is loading', (
    tester,
  ) async {
    final selectionResponse = Completer<dynamic>();
    final api = _FakeApiClient([
      () async => {
        'text': 'Выберите услугу',
        'state': <String, dynamic>{},
        'items': [
          {
            'type': 'service',
            'value': 'Стрижка',
            'name': 'Стрижка',
            'duration_minutes': 45,
          },
        ],
      },
      () => selectionResponse.future,
    ]);
    await tester.pumpWidget(_app(api));
    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();

    final card = find.byKey(const Key('aiResult-service-0'));
    await tester.ensureVisible(card);
    await tester.pump();
    await tester.tap(card);
    await tester.pump();
    await tester.ensureVisible(card);
    await tester.pump();
    await tester.tap(card);
    await tester.pump();

    expect(api.calls, 2);
    expect(
      tester
          .widget<ListTile>(
            find.descendant(of: card, matching: find.byType(ListTile)),
          )
          .onTap,
      isNull,
    );
    selectionResponse.complete({
      'text': 'Готово',
      'state': <String, dynamic>{'service': 'Стрижка'},
      'items': <dynamic>[],
    });
    await tester.pumpAndSettle();
  });

  testWidgets('unsupported explicit item is rendered without a tap action', (
    tester,
  ) async {
    final api = _FakeApiClient([
      () async => {
        'text': 'Дополнительная информация',
        'state': <String, dynamic>{},
        'items': [
          {'type': 'unsupported', 'name': 'Неизвестный вариант'},
        ],
      },
    ]);
    await tester.pumpWidget(_app(api));

    await tester.tap(find.byKey(const Key('aiQuickAction-0')));
    await tester.pumpAndSettle();

    final card = find.byKey(const Key('aiResult-unknown-0'));
    expect(card, findsOneWidget);
    expect(
      tester
          .widget<ListTile>(
            find.descendant(of: card, matching: find.byType(ListTile)),
          )
          .onTap,
      isNull,
    );
    expect(
      find.descendant(
        of: card,
        matching: find.byIcon(Icons.chevron_right_rounded),
      ),
      findsNothing,
    );
    await tester.tap(card);
    await tester.pump();
    expect(api.calls, 1);
  });
}
