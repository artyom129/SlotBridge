import 'dart:io';

import 'package:flutter/foundation.dart';

abstract final class AppConfig {
  static const _definedBaseUrl = String.fromEnvironment(
    'SLOTBRIDGE_API_BASE_URL',
    defaultValue: kReleaseMode ? 'https://slotbridge-api.onrender.com' : '',
  );
  static const _environment = String.fromEnvironment(
    'SLOTBRIDGE_ENVIRONMENT',
    defaultValue: kReleaseMode ? 'production' : 'development',
  );

  static String get apiBaseUrl => resolveApiBaseUrl(
    definedBaseUrl: _definedBaseUrl,
    environment: _environment,
    releaseMode: kReleaseMode,
    isAndroid: Platform.isAndroid,
  );

  static bool get isProduction =>
      kReleaseMode || _environment.trim().toLowerCase() == 'production';

  static String resolveApiBaseUrl({
    required String definedBaseUrl,
    required String environment,
    required bool releaseMode,
    required bool isAndroid,
  }) {
    final isProduction =
        releaseMode || environment.trim().toLowerCase() == 'production';
    final value = definedBaseUrl.trim();

    if (value.isEmpty) {
      if (isProduction) {
        throw StateError(
          'SLOTBRIDGE_API_BASE_URL is required for production builds.',
        );
      }
      return isAndroid ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000';
    }

    final uri = Uri.tryParse(value);
    if (uri == null ||
        !uri.hasAuthority ||
        uri.host.isEmpty ||
        !{'http', 'https'}.contains(uri.scheme) ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.userInfo.isNotEmpty) {
      throw StateError('SLOTBRIDGE_API_BASE_URL must be a valid HTTP(S) URL.');
    }
    if (isProduction && uri.scheme != 'https') {
      throw StateError(
        'SLOTBRIDGE_API_BASE_URL must use HTTPS in production builds.',
      );
    }

    return _withoutTrailingSlash(value);
  }

  static String _withoutTrailingSlash(String value) {
    return value.endsWith('/') ? value.substring(0, value.length - 1) : value;
  }
}
