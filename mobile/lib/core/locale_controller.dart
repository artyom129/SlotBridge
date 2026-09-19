import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final localeControllerProvider =
    AsyncNotifierProvider<LocaleController, Locale>(LocaleController.new);

class LocaleController extends AsyncNotifier<Locale> {
  static const _storage = FlutterSecureStorage();
  @override
  Future<Locale> build() async {
    final value = await _storage.read(key: 'slotbridge_locale');
    return Locale(value == 'en' ? 'en' : 'ru');
  }

  Future<void> select(String languageCode) async {
    final value = languageCode == 'en' ? 'en' : 'ru';
    await _storage.write(key: 'slotbridge_locale', value: value);
    state = AsyncData(Locale(value));
  }
}
