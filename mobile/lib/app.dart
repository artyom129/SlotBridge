import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';
import 'l10n/app_localizations.dart';
import 'core/locale_controller.dart';
import 'core/providers.dart';
import 'core/update/app_updater.dart';
import 'core/theme/theme_controller.dart';

class SlotBridgeApp extends ConsumerWidget {
  const SlotBridgeApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'SlotBridge',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ref.watch(themeControllerProvider).value ?? ThemeMode.system,
      locale: ref.watch(localeControllerProvider).value ?? const Locale('ru'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      routerConfig: ref.watch(appRouterProvider),
      builder: (context, child) => UpdateGate(
        api: ref.watch(apiClientProvider),
        child: child ?? const SizedBox.shrink(),
      ),
    );
  }
}
