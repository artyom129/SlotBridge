import 'package:dio/dio.dart';

class AppException implements Exception {
  const AppException(this.message, {this.code, this.statusCode});

  final String message;
  final String? code;
  final int? statusCode;

  factory AppException.fromDio(DioException error) {
    final response = error.response;
    final data = response?.data;
    String? code;
    String? message;

    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is Map<String, dynamic>) {
        code = detail['code']?.toString();
        message = detail['message']?.toString();
      } else if (detail is String) {
        message = detail;
      }
    }

    code ??= switch (error.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout => 'timeout',
      DioExceptionType.connectionError => 'connection_error',
      _ => 'unexpected_error',
    };

    message ??= switch (error.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout =>
        'Сервер не ответил вовремя. Попробуйте ещё раз.',
      DioExceptionType.connectionError =>
        'Не удалось подключиться к SlotBridge.',
      _ => 'Что-то пошло не так. Попробуйте ещё раз.',
    };

    return AppException(message, code: code, statusCode: response?.statusCode);
  }

  @override
  String toString() => message;
}
