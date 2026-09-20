import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/update/app_updater.dart';

void main() {
  test('same version is silent and newer version is offered', () {
    expect(shouldOfferUpdate(5, {'version_code': 5}), isFalse);
    expect(shouldOfferUpdate(5, {'version_code': 6}), isTrue);
  });
  test('only a complete SHA-256 value reaches native installer', () {
    expect(isValidSha256('a' * 64), isTrue);
    expect(isValidSha256('wrong'), isFalse);
  });
}
