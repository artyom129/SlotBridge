import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors/app_exception.dart';
import '../../core/providers.dart';

enum AiFailureKind {
  timeout,
  backendUnavailable,
  rateLimited,
  geminiUnavailable,
  auth,
  invalidResponse,
  unknown,
}

AiFailureKind classifyAiFailure(Object error) {
  if (error is FormatException || error is TypeError) {
    return AiFailureKind.invalidResponse;
  }
  if (error is! AppException) return AiFailureKind.unknown;
  if (error.statusCode == 401 || error.statusCode == 403) {
    return AiFailureKind.auth;
  }
  if (error.code == 'timeout' || error.code == 'AI_GEMINI_TIMEOUT') {
    return AiFailureKind.timeout;
  }
  if (error.code == 'connection_error' || error.code == 'AI_GEMINI_NETWORK') {
    return AiFailureKind.backendUnavailable;
  }
  if (error.code == 'AI_INVALID_RESPONSE' ||
      error.code == 'AI_GEMINI_REQUEST_REJECTED') {
    return AiFailureKind.invalidResponse;
  }
  if (error.code == 'AI_GEMINI_RATE_LIMIT') {
    return AiFailureKind.rateLimited;
  }
  if (error.code == 'AI_UNAVAILABLE' ||
      (error.code?.startsWith('AI_GEMINI_') ?? false)) {
    return AiFailureKind.geminiUnavailable;
  }
  if (error.statusCode != null && error.statusCode! >= 500) {
    return AiFailureKind.backendUnavailable;
  }
  return AiFailureKind.unknown;
}

class AiAssistantScreen extends ConsumerStatefulWidget {
  const AiAssistantScreen({super.key});

  @override
  ConsumerState<AiAssistantScreen> createState() => _AiAssistantScreenState();
}

class _AiAssistantScreenState extends ConsumerState<AiAssistantScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();
  final _messages = <({bool user, String text})>[];

  Map<String, dynamic> _conversationState = {};
  List<Map<String, dynamic>> _items = [];
  String? _confirmationToken;
  String? _lastFailedMessage;
  bool _loading = false;
  bool _confirming = false;
  bool _confirmationError = false;
  bool _hasError = false;
  AiFailureKind _failureKind = AiFailureKind.unknown;
  bool _waitingForColdStart = false;
  bool _retryingAutomatically = false;
  String? _activeQuickAction;
  Timer? _slowRequestTimer;

  bool get _isEnglish => Localizations.localeOf(context).languageCode == 'en';

  List<String> get _quickActions => _isEnglish
      ? const [
          'Find a time',
          'Book appointment',
          'My appointments',
          'Reschedule',
          'Best time',
        ]
      : const [
          'Найти время',
          'Записаться',
          'Мои записи',
          'Перенести запись',
          'Лучший слот',
        ];

  Future<void> _send([String? value]) async {
    final text = (value ?? _inputController.text).trim();
    await _submitMessage(text, appendUserMessage: true, quickAction: value);
  }

  Future<void> _submitMessage(
    String text, {
    required bool appendUserMessage,
    String? quickAction,
  }) async {
    if (text.isEmpty || _loading) return;
    FocusManager.instance.primaryFocus?.unfocus();
    setState(() {
      if (appendUserMessage) {
        _messages.add((user: true, text: text));
        _inputController.clear();
      }
      _loading = true;
      _confirming = false;
      _confirmationError = false;
      _hasError = false;
      _failureKind = AiFailureKind.unknown;
      _lastFailedMessage = text;
      _confirmationToken = null;
      _items = [];
      _activeQuickAction = quickAction;
      _waitingForColdStart = false;
      _retryingAutomatically = false;
    });
    _slowRequestTimer?.cancel();
    _slowRequestTimer = Timer(const Duration(seconds: 8), () {
      if (mounted && _loading) {
        setState(() => _waitingForColdStart = true);
      }
    });
    _scrollToBottom();

    try {
      final raw = await _postChatWithRetry(text);
      if (!mounted) return;
      if (raw is! Map) {
        throw const FormatException('AI response is not an object');
      }
      final response = raw.cast<String, dynamic>();
      final responseText = response['text']?.toString().trim() ?? '';
      final rawItems = response['items'];
      setState(() {
        if (responseText.isNotEmpty) {
          _messages.add((user: false, text: responseText));
        }
        _conversationState =
            (response['state'] as Map?)?.cast<String, dynamic>() ?? {};
        _items = rawItems is List
            ? rawItems
                  .whereType<Map>()
                  .map((item) => item.cast<String, dynamic>())
                  .toList(growable: false)
            : [];
        final token = response['confirmation_token']?.toString().trim();
        _confirmationToken = token == null || token.isEmpty ? null : token;
        _lastFailedMessage = null;
      });
    } catch (error) {
      if (!mounted) return;
      final failureKind = classifyAiFailure(error);
      _logSafeFailure(error, failureKind);
      setState(() {
        _hasError = true;
        _failureKind = failureKind;
        _confirmationError = false;
      });
    } finally {
      _slowRequestTimer?.cancel();
      if (mounted) {
        setState(() {
          _loading = false;
          _activeQuickAction = null;
          _waitingForColdStart = false;
          _retryingAutomatically = false;
        });
        _scrollToBottom();
      }
    }
  }

  Future<dynamic> _postChatWithRetry(String text) async {
    for (var attempt = 0; attempt < 2; attempt++) {
      try {
        return await ref
            .read(apiClientProvider)
            .post(
              '/ai/chat',
              data: {
                'message': text,
                'locale': _isEnglish ? 'en' : 'ru',
                'state': _conversationState,
              },
            );
      } catch (error) {
        if (attempt == 1 || !_isTemporaryAiError(error)) rethrow;
        if (mounted) {
          setState(() => _retryingAutomatically = true);
        }
        await Future<void>.delayed(const Duration(milliseconds: 1200));
      }
    }
    throw StateError('AI retry exhausted');
  }

  bool _isTemporaryAiError(Object error) {
    if (error is! AppException) return false;
    if (const {
      'AI_GEMINI_AUTH',
      'AI_GEMINI_MODEL_UNAVAILABLE',
      'AI_GEMINI_REQUEST_REJECTED',
      'AI_GEMINI_RATE_LIMIT',
      'AI_INVALID_RESPONSE',
    }.contains(error.code)) {
      return false;
    }
    return const {
          'timeout',
          'connection_error',
          'AI_UNAVAILABLE',
          'AI_GEMINI_TIMEOUT',
          'AI_GEMINI_NETWORK',
          'AI_GEMINI_UNAVAILABLE',
        }.contains(error.code) ||
        const {502, 503, 504}.contains(error.statusCode);
  }

  void _logSafeFailure(Object error, AiFailureKind kind) {
    final appError = error is AppException ? error : null;
    debugPrint(
      'SlotBridge AI failure '
      'kind=${kind.name} '
      'code=${appError?.code ?? 'invalid_response'} '
      'status=${appError?.statusCode ?? 'none'}',
    );
  }

  Future<void> _confirm() async {
    final token = _confirmationToken;
    if (token == null || _loading) return;
    setState(() {
      _loading = true;
      _confirming = true;
      _hasError = false;
      _failureKind = AiFailureKind.unknown;
      _confirmationError = false;
    });
    _scrollToBottom();
    try {
      await ref
          .read(apiClientProvider)
          .post('/ai/confirm', data: {'confirmation_token': token});
      if (!mounted) return;
      setState(() {
        _confirmationToken = null;
        _messages.add((
          user: false,
          text: _isEnglish
              ? 'Done. Your appointment data is updated.'
              : 'Готово. Данные вашей записи обновлены.',
        ));
      });
    } catch (error) {
      if (!mounted) return;
      final failureKind = classifyAiFailure(error);
      _logSafeFailure(error, failureKind);
      setState(() {
        _hasError = true;
        _failureKind = failureKind;
        _confirmationError = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _confirming = false;
        });
        _scrollToBottom();
      }
    }
  }

  Future<void> _retry() async {
    if (_loading) return;
    if (_confirmationError && _confirmationToken != null) {
      await _confirm();
      return;
    }
    final message = _lastFailedMessage;
    if (message != null) {
      await _submitMessage(message, appendUserMessage: false);
    }
  }

  void _cancelConfirmation() {
    if (_loading) return;
    setState(() {
      _confirmationToken = null;
      _hasError = false;
      _failureKind = AiFailureKind.unknown;
      _confirmationError = false;
      _messages.add((
        user: false,
        text: _isEnglish ? 'Action cancelled.' : 'Действие отменено.',
      ));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  void dispose() {
    _slowRequestTimer?.cancel();
    _inputController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('SlotBridge AI')),
      body: SafeArea(
        top: false,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      _isEnglish
                          ? 'Manage bookings with a message'
                          : 'Запишитесь обычным сообщением',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                _QuickActions(
                  actions: _quickActions,
                  enabled: !_loading,
                  activeAction: _activeQuickAction,
                  onPressed: _send,
                ),
                const SizedBox(height: 6),
                Expanded(
                  child: ListView(
                    key: const Key('aiConversationList'),
                    controller: _scrollController,
                    keyboardDismissBehavior:
                        ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                    children: [
                      if (_messages.isEmpty && !_loading)
                        _IntroCard(isEnglish: _isEnglish),
                      ..._messages.map(
                        (message) => _MessageBubble(
                          user: message.user,
                          text: message.text,
                        ),
                      ),
                      ..._items.take(6).map((item) => _ResultCard(item: item)),
                      if (_confirmationToken != null)
                        _ConfirmationCard(
                          isEnglish: _isEnglish,
                          loading: _loading,
                          onConfirm: _confirm,
                          onCancel: _cancelConfirmation,
                        ),
                      if (_hasError)
                        _AiErrorCard(
                          isEnglish: _isEnglish,
                          loading: _loading,
                          failureKind: _failureKind,
                          onRetry: _retry,
                        ),
                      if (_loading)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const SizedBox.square(
                                dimension: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Flexible(
                                child: Text(
                                  _confirming
                                      ? (_isEnglish
                                            ? 'Confirming action…'
                                            : 'Подтверждаем действие…')
                                      : _retryingAutomatically
                                      ? (_isEnglish
                                            ? 'Retrying the connection…'
                                            : 'Повторно подключаемся…')
                                      : _waitingForColdStart
                                      ? (_isEnglish
                                            ? 'The server is starting. This may take a little longer…'
                                            : 'Сервер запускается. Это может занять немного больше времени…')
                                      : (_isEnglish
                                            ? 'SlotBridge AI is thinking…'
                                            : 'SlotBridge AI думает…'),
                                  style: TextStyle(
                                    color: colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
                _Composer(
                  controller: _inputController,
                  focusNode: _focusNode,
                  enabled: !_loading,
                  isEnglish: _isEnglish,
                  onSend: _send,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions({
    required this.actions,
    required this.enabled,
    required this.activeAction,
    required this.onPressed,
  });

  final List<String> actions;
  final bool enabled;
  final String? activeAction;
  final ValueChanged<String> onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 56,
    child: ListView.separated(
      key: const Key('aiQuickActionsList'),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      scrollDirection: Axis.horizontal,
      itemCount: actions.length,
      separatorBuilder: (_, _) => const SizedBox(width: 8),
      itemBuilder: (context, index) => SizedBox(
        width: 148,
        height: 56,
        child: OutlinedButton(
          key: Key('aiQuickAction-$index'),
          onPressed: enabled ? () => onPressed(actions[index]) : null,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(48, 56),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            tapTargetSize: MaterialTapTargetSize.padded,
          ),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 150),
            child: activeAction == actions[index]
                ? Row(
                    key: const ValueKey('loading'),
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          actions[index],
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ],
                  )
                : Text(
                    actions[index],
                    key: const ValueKey('label'),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                  ),
          ),
        ),
      ),
    ),
  );
}

class _IntroCard extends StatelessWidget {
  const _IntroCard({required this.isEnglish});

  final bool isEnglish;

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.surfaceContainerHighest,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.auto_awesome_rounded),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              isEnglish
                  ? 'Ask about services, available times, or your appointments.'
                  : 'Спросите об услугах, свободном времени или своих записях.',
            ),
          ),
        ],
      ),
    ),
  );
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.user, required this.text});

  final bool user;
  final String text;

  @override
  Widget build(BuildContext context) => Align(
    alignment: user ? Alignment.centerRight : Alignment.centerLeft,
    child: FractionallySizedBox(
      widthFactor: 0.86,
      alignment: user ? Alignment.centerRight : Alignment.centerLeft,
      child: Card(
        color: user
            ? Theme.of(context).colorScheme.primaryContainer
            : Theme.of(context).colorScheme.surfaceContainerLow,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          child: Text(text, softWrap: true),
        ),
      ),
    ),
  );
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final rawSteps = item['steps'];
    if (item['strategy'] != null && rawSteps is List) {
      final isEnglish = Localizations.localeOf(context).languageCode == 'en';
      final strategy = item['strategy']?.toString();
      final title = switch (strategy) {
        'FASTEST' => isEnglish ? 'Fastest' : 'Быстрее всего',
        'EARLIEST' => isEnglish ? 'Earliest possible' : 'Как можно раньше',
        _ => isEnglish ? 'Fewer specialists' : 'Меньше сотрудников',
      };
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              ...rawSteps.whereType<Map>().map(
                (step) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 96,
                        child: Text(
                          step['time']?.toString() ?? '',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          '${step['service'] ?? ''}\n${step['employee'] ?? ''}',
                          maxLines: 4,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Wrap(
                spacing: 12,
                runSpacing: 4,
                children: [
                  Text(
                    isEnglish
                        ? 'Total: ${item['total_minutes']} min'
                        : 'Всего: ${item['total_minutes']} мин',
                  ),
                  Text(
                    isEnglish
                        ? 'Waiting: ${item['wait_minutes']} min'
                        : 'Ожидание: ${item['wait_minutes']} мин',
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }
    final title = (item['time'] ?? item['service'] ?? item['name'] ?? '')
        .toString();
    final subtitle = item['employee']?.toString();
    return Card(
      child: ListTile(
        minVerticalPadding: 12,
        leading: Icon(
          item['reason'] != null ? Icons.star_rounded : Icons.schedule_rounded,
        ),
        title: Text(title, maxLines: 3, overflow: TextOverflow.ellipsis),
        subtitle: subtitle == null
            ? null
            : Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis),
      ),
    );
  }
}

class _ConfirmationCard extends StatelessWidget {
  const _ConfirmationCard({
    required this.isEnglish,
    required this.loading,
    required this.onConfirm,
    required this.onCancel,
  });

  final bool isEnglish;
  final bool loading;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.secondaryContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.verified_user_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isEnglish
                          ? 'Confirmation required'
                          : 'Нужно подтверждение',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isEnglish
                          ? 'Check the details above. Nothing will change until you confirm.'
                          : 'Проверьте данные выше. До подтверждения ничего не изменится.',
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: 8,
            runSpacing: 8,
            children: [
              TextButton(
                key: const Key('aiCancelConfirmationButton'),
                onPressed: loading ? null : onCancel,
                child: Text(isEnglish ? 'Cancel' : 'Отменить'),
              ),
              FilledButton.icon(
                key: const Key('aiConfirmButton'),
                onPressed: loading ? null : onConfirm,
                icon: const Icon(Icons.check_rounded),
                label: Text(isEnglish ? 'Confirm' : 'Подтвердить'),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _AiErrorCard extends StatelessWidget {
  const _AiErrorCard({
    required this.isEnglish,
    required this.loading,
    required this.failureKind,
    required this.onRetry,
  });

  final bool isEnglish;
  final bool loading;
  final AiFailureKind failureKind;
  final VoidCallback onRetry;

  String get message => switch ((isEnglish, failureKind)) {
    (true, AiFailureKind.timeout) =>
      'The AI request took too long. Please try again.',
    (false, AiFailureKind.timeout) =>
      'AI не ответил вовремя. Попробуйте ещё раз.',
    (true, AiFailureKind.backendUnavailable) =>
      'Could not reach SlotBridge. Check your connection and try again.',
    (false, AiFailureKind.backendUnavailable) =>
      'Не удалось связаться со SlotBridge. Проверьте интернет и повторите.',
    (true, AiFailureKind.rateLimited) =>
      'Gemini is receiving too many requests. Wait a moment and try again.',
    (false, AiFailureKind.rateLimited) =>
      'Gemini получил слишком много запросов. Подождите немного и повторите.',
    (true, AiFailureKind.geminiUnavailable) =>
      'Gemini is temporarily unavailable. Regular booking still works.',
    (false, AiFailureKind.geminiUnavailable) =>
      'Gemini временно недоступен. Обычная запись продолжает работать.',
    (true, AiFailureKind.auth) =>
      'Your session has expired. Sign in again to use SlotBridge AI.',
    (false, AiFailureKind.auth) =>
      'Сессия истекла. Войдите снова, чтобы использовать SlotBridge AI.',
    (true, AiFailureKind.invalidResponse) =>
      'AI returned an invalid response. Please try again.',
    (false, AiFailureKind.invalidResponse) =>
      'AI вернул некорректный ответ. Попробуйте ещё раз.',
    (true, _) => 'AI Assistant could not complete the request. Regular booking still works.',
    (false, _) => 'AI-помощник не смог выполнить запрос. Обычная запись продолжает работать.',
  };

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.errorContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(message),
          if (failureKind != AiFailureKind.auth) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.tonalIcon(
                key: const Key('aiRetryButton'),
                onPressed: loading ? null : onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(isEnglish ? 'Try again' : 'Повторить'),
              ),
            ),
          ],
        ],
      ),
    ),
  );
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.focusNode,
    required this.enabled,
    required this.isEnglish,
    required this.onSend,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final bool enabled;
  final bool isEnglish;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) => Material(
    color: Theme.of(context).colorScheme.surface,
    elevation: 3,
    child: SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(16, 10, 16, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              key: const Key('aiMessageInput'),
              controller: controller,
              focusNode: focusNode,
              enabled: enabled,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              decoration: InputDecoration(
                hintText: isEnglish
                    ? 'Message SlotBridge AI'
                    : 'Сообщение SlotBridge AI',
              ),
              onSubmitted: enabled ? (_) => onSend() : null,
              onTapOutside: (_) => focusNode.unfocus(),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox.square(
            dimension: 48,
            child: IconButton.filled(
              key: const Key('aiSendButton'),
              tooltip: isEnglish ? 'Send' : 'Отправить',
              onPressed: enabled ? onSend : null,
              icon: enabled
                  ? const Icon(Icons.send_rounded)
                  : const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
            ),
          ),
        ],
      ),
    ),
  );
}
