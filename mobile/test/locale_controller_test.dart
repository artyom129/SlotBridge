import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/locale_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('language switch is immediate and persists', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final first = ProviderContainer();
    addTearDown(first.dispose);
    await first.read(localeControllerProvider.future);
    await first.read(localeControllerProvider.notifier).select('en');
    expect(first.read(localeControllerProvider).value?.languageCode, 'en');
    final second = ProviderContainer();
    addTearDown(second.dispose);
    expect(
      (await second.read(localeControllerProvider.future)).languageCode,
      'en',
    );
  });
}
