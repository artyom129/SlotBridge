import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/locale_controller.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/ui/widgets.dart';
import '../../l10n/l10n.dart';
import '../auth/auth_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  Future<void> _edit(BuildContext context, WidgetRef ref) async {
    final user = ref.read(authControllerProvider).value;
    if (user == null) return;
    final first = TextEditingController(text: user.firstName),
        last = TextEditingController(text: user.lastName),
        phone = TextEditingController(text: user.phone ?? '');
    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.editProfile),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: first,
                decoration: InputDecoration(
                  labelText: context.l10n.firstNameLabel,
                ),
              ),
              TextField(
                controller: last,
                decoration: InputDecoration(
                  labelText: context.l10n.lastNameLabel,
                ),
              ),
              TextField(
                controller: phone,
                decoration: InputDecoration(
                  labelText: context.l10n.phoneOptionalLabel,
                ),
              ),
              TextFormField(
                initialValue: user.email,
                enabled: false,
                decoration: InputDecoration(labelText: context.l10n.emailLabel),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.l10n.back),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.l10n.save),
          ),
        ],
      ),
    );
    if (save == true) {
      await ref
          .read(authControllerProvider.notifier)
          .updateProfile(
            firstName: first.text,
            lastName: last.text,
            phone: phone.text,
          );
    }
    first.dispose();
    last.dispose();
    phone.dispose();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).value;
    final locale =
        ref.watch(localeControllerProvider).value ?? const Locale('ru');
    final theme = ref.watch(themeControllerProvider).value ?? ThemeMode.system;
    final initials = user == null
        ? 'С'
        : '${user.firstName.characters.first}${user.lastName.characters.first}'
              .toUpperCase();
    return Scaffold(
      appBar: AppBar(title: Text(context.l10n.profile)),
      body: PageBody(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  children: [
                    CircleAvatar(radius: 34, child: Text(initials)),
                    const SizedBox(height: 12),
                    Text(
                      user?.displayName ?? context.l10n.client,
                      style: Theme.of(context).textTheme.titleLarge
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    Text(user?.email ?? ''),
                    const SizedBox(height: 6),
                    Chip(label: Text(context.l10n.client)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.edit_outlined),
                    title: Text(context.l10n.editProfile),
                    onTap: () => _edit(context, ref),
                  ),
                  ListTile(
                    leading: const Icon(Icons.language_rounded),
                    title: Text(context.l10n.language),
                    subtitle: Text(
                      locale.languageCode == 'en'
                          ? context.l10n.english
                          : context.l10n.russian,
                    ),
                    onTap: () => ref
                        .read(localeControllerProvider.notifier)
                        .select(locale.languageCode == 'en' ? 'ru' : 'en'),
                  ),
                  ListTile(
                    leading: const Icon(Icons.palette_outlined),
                    title: Text(context.l10n.theme),
                    subtitle: Text(
                      locale.languageCode == 'en'
                          ? switch (theme) {
                              ThemeMode.light => 'Light',
                              ThemeMode.dark => 'Dark',
                              _ => 'System',
                            }
                          : switch (theme) {
                              ThemeMode.light => 'Светлая',
                              ThemeMode.dark => 'Тёмная',
                              _ => 'Системная',
                            },
                    ),
                    onTap: () =>
                        ref.read(themeControllerProvider.notifier).cycle(),
                  ),
                  ListTile(
                    leading: const Icon(Icons.event_note_rounded),
                    title: Text(context.l10n.myAppointments),
                    onTap: () => context.go('/appointments'),
                  ),
                  ListTile(
                    leading: const Icon(Icons.hourglass_top_rounded),
                    title: Text(context.l10n.waitlist),
                  ),
                  ListTile(
                    leading: const Icon(Icons.info_outline_rounded),
                    title: Text(context.l10n.about),
                    subtitle: Text('${context.l10n.version} 1.1.0 (4)'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () =>
                  ref.read(authControllerProvider.notifier).logout(),
              icon: const Icon(Icons.logout_rounded),
              label: Text(context.l10n.signOut),
            ),
          ],
        ),
      ),
    );
  }
}
