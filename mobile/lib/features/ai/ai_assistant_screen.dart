import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';

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
    await _submitMessage(text, appendUserMessage: true);
  }

  Future<void> _submitMessage(
    String text, {
    required bool appendUserMessage,
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
      _lastFailedMessage = text;
      _confirmationToken = null;
      _items = [];
    });
    _scrollToBottom();

    try {
      final raw = await ref
          .read(apiClientProvider)
          .post(
            '/ai/chat',
            data: {
              'message': text,
              'locale': _isEnglish ? 'en' : 'ru',
              'state': _conversationState,
            },
          );
      if (!mounted) return;
      final response = (raw as Map).cast<String, dynamic>();
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
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _hasError = true;
        _confirmationError = false;
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
        _scrollToBottom();
      }
    }
  }

  Future<void> _confirm() async {
    final token = _confirmationToken;
    if (token == null || _loading) return;
    setState(() {
      _loading = true;
      _confirming = true;
      _hasError = false;
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
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _hasError = true;
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
                Expanded(
                  child: ListView(
                    key: const Key('aiConversationList'),
                    controller: _scrollController,
                    keyboardDismissBehavior:
                        ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                    children: [
                      Text(
                        _isEnglish
                            ? 'Manage bookings with a message'
                            : 'Запишитесь обычным сообщением',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 12),
                      _QuickActions(
                        actions: _quickActions,
                        enabled: !_loading,
                        onPressed: _send,
                      ),
                      const SizedBox(height: 18),
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
    required this.onPressed,
  });

  final List<String> actions;
  final bool enabled;
  final ValueChanged<String> onPressed;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final buttonWidth = constraints.maxWidth < 360
          ? constraints.maxWidth
          : (constraints.maxWidth - 8) / 2;
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (var index = 0; index < actions.length; index++)
            SizedBox(
              width: buttonWidth,
              height: 52,
              child: OutlinedButton(
                key: Key('aiQuickAction-$index'),
                onPressed: enabled ? () => onPressed(actions[index]) : null,
                child: Text(
                  actions[index],
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                ),
              ),
            ),
        ],
      );
    },
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
    required this.onRetry,
  });

  final bool isEnglish;
  final bool loading;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.errorContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            isEnglish
                ? 'AI Assistant is temporarily unavailable. Regular booking still works.'
                : 'AI-помощник временно недоступен. Обычная запись продолжает работать.',
          ),
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
