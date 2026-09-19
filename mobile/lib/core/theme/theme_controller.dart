import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final themeControllerProvider =
    AsyncNotifierProvider<ThemeController, ThemeMode>(ThemeController.new);

class ThemeController extends AsyncNotifier<ThemeMode> {
  static const storage = FlutterSecureStorage();
  @override
  Future<ThemeMode> build() async =>
      switch (await storage.read(key: 'slotbridge_theme')) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };
  Future<void> cycle() async {
    final current = state.value ?? ThemeMode.system;
    final next = current == ThemeMode.system
        ? ThemeMode.light
        : current == ThemeMode.light
        ? ThemeMode.dark
        : ThemeMode.system;
    await storage.write(key: 'slotbridge_theme', value: next.name);
    state = AsyncData(next);
  }
}
