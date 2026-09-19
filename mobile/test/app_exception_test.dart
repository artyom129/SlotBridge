import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slotbridge_mobile/core/errors/app_exception.dart';

void main() {
  test('maps FastAPI domain error without exposing transport internals', () {
    final request = RequestOptions(path: '/appointments');
    final exception = AppException.fromDio(
      DioException(
        requestOptions: request,
        response: Response<dynamic>(
          requestOptions: request,
          statusCode: 409,
          data: {
            'detail': {
              'code': 'SLOT_ALREADY_BOOKED',
              'message': 'This time slot is no longer available.',
            },
          },
        ),
      ),
    );

    expect(exception.statusCode, 409);
    expect(exception.code, 'SLOT_ALREADY_BOOKED');
    expect(exception.message, 'This time slot is no longer available.');
  });
}
