import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/locale_controller.dart';
import '../../core/providers.dart';
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
        phone = TextEditingController(text: user.phone ?? ''),
        email = TextEditingController(text: user.email);
    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        key: const Key('editProfileDialog'),
        scrollable: true,
        insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
        title: Text(context.l10n.editProfile),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                key: const Key('editProfileFirstName'),
                controller: first,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: context.l10n.firstNameLabel,
                  prefixIcon: const Icon(Icons.person_outline_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('editProfileLastName'),
                controller: last,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: context.l10n.lastNameLabel,
                  prefixIcon: const Icon(Icons.person_outline_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('editProfilePhone'),
                controller: phone,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.done,
                decoration: InputDecoration(
                  labelText: context.l10n.phoneOptionalLabel,
                  prefixIcon: const Icon(Icons.phone_outlined),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('editProfileEmail'),
                controller: email,
                readOnly: true,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  labelText: context.l10n.emailLabel,
                  prefixIcon: const Icon(Icons.email_outlined),
                  suffixIcon: const Icon(Icons.lock_outline_rounded),
                ),
              ),
            ],
          ),
        ),
        actionsAlignment: MainAxisAlignment.end,
        actionsOverflowAlignment: OverflowBarAlignment.end,
        actionsPadding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        actions: [
          TextButton(
            key: const Key('editProfileBackButton'),
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.l10n.back),
          ),
          FilledButton(
            key: const Key('editProfileSaveButton'),
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.l10n.save),
          ),
        ],
      ),
    );
    if (save == true) {
      try {
        await ref
            .read(authControllerProvider.notifier)
            .updateProfile(
              firstName: first.text.trim(),
              lastName: last.text.trim(),
              phone: phone.text.trim(),
            );
      } catch (error) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(readableError(context, error))),
          );
        }
      }
    }
    first.dispose();
    last.dispose();
    phone.dispose();
    email.dispose();
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
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    Text(
                      user?.email ?? '',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                    ),
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
                    subtitle: Text(
                      locale.languageCode == 'en'
                          ? 'Available matches appear on Home'
                          : 'Доступные варианты появляются на главной',
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () {
                      ref.invalidate(waitlistProvider);
                      context.go('/home');
                    },
                  ),
                  ListTile(
                    leading: const Icon(Icons.info_outline_rounded),
                    title: Text(context.l10n.about),
                    subtitle: Text('${context.l10n.version} 1.1.2 (6)'),
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
