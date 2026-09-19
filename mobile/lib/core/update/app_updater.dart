import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/config/app_config.dart';
import '../../core/network/api_client.dart';

bool shouldOfferUpdate(
  int installedVersionCode,
  Map<String, dynamic> manifest,
) => (manifest['version_code'] as int? ?? 0) > installedVersionCode;
bool isValidSha256(String value) =>
    RegExp(r'^[0-9a-fA-F]{64}$').hasMatch(value);

class UpdateGate extends StatefulWidget {
  const UpdateGate({super.key, required this.child, required this.api});
  final Widget child;
  final ApiClient api;
  @override
  State<UpdateGate> createState() => _UpdateGateState();
}

class _UpdateGateState extends State<UpdateGate> {
  static const channel = MethodChannel('slotbridge/updater');
  final downloadProgress = ValueNotifier<double>(0);
  @override
  void initState() {
    super.initState();
    channel.setMethodCallHandler((call) async {
      if (call.method == 'progress') {
        downloadProgress.value = (call.arguments as num).toDouble();
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _check());
  }

  Future<void> _check() async {
    if (!AppConfig.isProduction || !Platform.isAndroid) return;
    try {
      if (await channel.invokeMethod<bool>('checkDue') != true) return;
      final current =
          await channel.invokeMethod<int>('installedVersionCode') ?? 0;
      final data =
          await widget.api.get('/api/v1/app/version') as Map<String, dynamic>;
      if (!shouldOfferUpdate(current, data) || !mounted) return;
      final locale = Localizations.localeOf(context).languageCode == 'en'
          ? 'en'
          : 'ru';
      final changes =
          ((data['changelog'] as Map<String, dynamic>)[locale] as List<dynamic>)
              .cast<String>();
      await showDialog<void>(
        context: context,
        barrierDismissible: data['required'] != true,
        builder: (context) => AlertDialog(
          title: Text(
            locale == 'en' ? 'Update available' : 'Доступно обновление',
          ),
          content: Text(
            [
              '${data['version_name']}',
              ...changes.map((e) => '• $e'),
            ].join('\n'),
          ),
          actions: [
            if (data['required'] != true)
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: Text(locale == 'en' ? 'Later' : 'Позже'),
              ),
            FilledButton(
              onPressed: () async {
                Navigator.pop(context);
                await _install(data, locale);
              },
              child: Text(locale == 'en' ? 'Update now' : 'Обновить сейчас'),
            ),
          ],
        ),
      );
    } catch (_) {
      /* fail open: booking must always remain available */
    }
  }

  Future<void> _install(Map<String, dynamic> data, String locale) async {
    if (!isValidSha256(data['sha256'] as String? ?? '')) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            locale == 'en'
                ? 'The update could not be verified.'
                : 'Не удалось проверить обновление.',
          ),
        ),
      );
      return;
    }
    downloadProgress.value = 0;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(
          locale == 'en' ? 'Downloading update' : 'Загрузка обновления',
        ),
        content: ValueListenableBuilder<double>(
          valueListenable: downloadProgress,
          builder: (_, value, _) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              LinearProgressIndicator(value: value == 0 ? null : value),
              const SizedBox(height: 10),
              Text('${(value * 100).round()}%'),
            ],
          ),
        ),
      ),
    );
    try {
      await channel.invokeMethod('downloadAndInstall', {
        'url': data['apk_url'],
        'sha256': data['sha256'],
      });
      if (mounted && Navigator.of(context, rootNavigator: true).canPop()) {
        Navigator.of(context, rootNavigator: true).pop();
      }
    } on PlatformException catch (_) {
      if (mounted && Navigator.of(context, rootNavigator: true).canPop()) {
        Navigator.of(context, rootNavigator: true).pop();
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              locale == 'en'
                  ? 'The update could not be verified.'
                  : 'Не удалось проверить обновление.',
            ),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => widget.child;

  @override
  void dispose() {
    channel.setMethodCallHandler(null);
    downloadProgress.dispose();
    super.dispose();
  }
}
