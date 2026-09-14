import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/config/app_config.dart';

void main() {
  group('AppConfig', () {
    test('uses the Android emulator URL only for local development', () {
      expect(
        AppConfig.resolveApiBaseUrl(
          definedBaseUrl: '',
          environment: 'development',
          releaseMode: false,
          isAndroid: true,
        ),
        'http://10.0.2.2:8000',
      );
    });

    test('accepts an explicit LAN URL in a debug build', () {
      expect(
        AppConfig.resolveApiBaseUrl(
          definedBaseUrl: 'http://192.168.100.7:8000/',
          environment: 'development',
          releaseMode: false,
          isAndroid: true,
        ),
        'http://192.168.100.7:8000',
      );
    });

    test('requires an explicit URL for production', () {
      expect(
        () => AppConfig.resolveApiBaseUrl(
          definedBaseUrl: '',
          environment: 'production',
          releaseMode: false,
          isAndroid: true,
        ),
        throwsStateError,
      );
    });

    test('rejects cleartext HTTP for release builds', () {
      expect(
        () => AppConfig.resolveApiBaseUrl(
          definedBaseUrl: 'http://api.example.com',
          environment: 'development',
          releaseMode: true,
          isAndroid: true,
        ),
        throwsStateError,
      );
    });

    test('accepts and normalizes a production HTTPS URL', () {
      expect(
        AppConfig.resolveApiBaseUrl(
          definedBaseUrl: 'https://api.example.com/',
          environment: 'production',
          releaseMode: true,
          isAndroid: true,
        ),
        'https://api.example.com',
      );
    });
  });
}
