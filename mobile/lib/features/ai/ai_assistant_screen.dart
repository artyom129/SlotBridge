import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/ui/widgets.dart';

class AiAssistantScreen extends ConsumerStatefulWidget {
  const AiAssistantScreen({super.key});
  @override
  ConsumerState<AiAssistantScreen> createState() => _AiAssistantScreenState();
}

class _AiAssistantScreenState extends ConsumerState<AiAssistantScreen> {
  final controller = TextEditingController();
  final messages = <({bool user, String text})>[];
  Map<String, dynamic> state = {};
  List<dynamic> items = [];
  String? confirmationToken;
  bool loading = false;
  bool get en => Localizations.localeOf(context).languageCode == 'en';

  Future<void> send([String? value]) async {
    final text = (value ?? controller.text).trim();
    if (text.isEmpty || loading) return;
    setState(() {
      messages.add((user: true, text: text));
      loading = true;
      controller.clear();
      confirmationToken = null;
      items = [];
    });
    try {
      final response =
          await ref
                  .read(apiClientProvider)
                  .post(
                    '/ai/chat',
                    data: {
                      'message': text,
                      'locale': en ? 'en' : 'ru',
                      'state': state,
                    },
                  )
              as Map<String, dynamic>;
      setState(() {
        messages.add((user: false, text: response['text'] as String));
        state = (response['state'] as Map?)?.cast<String, dynamic>() ?? {};
        items = response['items'] as List<dynamic>? ?? [];
        confirmationToken = response['confirmation_token'] as String?;
      });
    } catch (_) {
      setState(
        () => messages.add((
          user: false,
          text: en
              ? 'AI Assistant is temporarily unavailable. You can continue with regular booking.'
              : 'AI-помощник сейчас недоступен. Вы можете записаться обычным способом.',
        )),
      );
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> confirm() async {
    final token = confirmationToken;
    if (token == null) return;
    setState(() => loading = true);
    try {
      await ref
          .read(apiClientProvider)
          .post('/ai/confirm', data: {'confirmation_token': token});
      setState(() {
        confirmationToken = null;
        messages.add((
          user: false,
          text: en
              ? 'Done. Your appointment data is updated.'
              : 'Готово. Данные вашей записи обновлены.',
        ));
      });
    } catch (_) {
      setState(
        () => messages.add((
          user: false,
          text: en
              ? 'The action could not be completed. Please choose another time.'
              : 'Не удалось выполнить действие. Выберите другое время.',
        )),
      );
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final actions = en
        ? [
            'Find a time',
            'Book appointment',
            'My appointments',
            'Reschedule',
            'Best time',
          ]
        : [
            'Найти время',
            'Записаться',
            'Мои записи',
            'Перенести запись',
            'Лучший слот',
          ];
    return Scaffold(
      appBar: AppBar(title: const Text('SlotBridge AI')),
      body: PageBody(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              en
                  ? 'Manage bookings with a message'
                  : 'Запишитесь обычным сообщением',
              style: Theme.of(context).textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: actions
                  .map(
                    (x) => ActionChip(label: Text(x), onPressed: () => send(x)),
                  )
                  .toList(),
            ),
            const SizedBox(height: 16),
            ...messages.map(
              (m) => Align(
                alignment: m.user
                    ? Alignment.centerRight
                    : Alignment.centerLeft,
                child: Card(
                  color: m.user
                      ? Theme.of(context).colorScheme.primaryContainer
                      : null,
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Text(m.text),
                  ),
                ),
              ),
            ),
            ...items.take(6).map((raw) {
              final item = (raw as Map).cast<String, dynamic>();
              return Card(
                child: ListTile(
                  leading: item['reason'] != null
                      ? const Icon(Icons.star_rounded)
                      : const Icon(Icons.schedule_rounded),
                  title: Text(
                    (item['time'] ?? item['service'] ?? item['name'] ?? '')
                        .toString(),
                  ),
                  subtitle: item['employee'] == null
                      ? null
                      : Text(item['employee'].toString()),
                ),
              );
            }),
            if (confirmationToken != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: FilledButton.icon(
                  onPressed: loading ? null : confirm,
                  icon: const Icon(Icons.check_rounded),
                  label: Text(en ? 'Confirm' : 'Подтвердить'),
                ),
              ),
            if (loading)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    minLines: 1,
                    maxLines: 4,
                    decoration: InputDecoration(
                      hintText: en
                          ? 'Message SlotBridge AI'
                          : 'Сообщение SlotBridge AI',
                    ),
                    onSubmitted: (_) => send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: loading ? null : send,
                  icon: const Icon(Icons.send_rounded),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
