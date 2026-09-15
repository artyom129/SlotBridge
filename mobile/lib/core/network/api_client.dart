import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../errors/app_exception.dart';
import '../storage/token_storage.dart';

class ApiClient {
  ApiClient(this._tokenStorage, {Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: AppConfig.apiBaseUrl,
              connectTimeout: Duration(
                seconds: AppConfig.isProduction ? 30 : 12,
              ),
              receiveTimeout: Duration(
                seconds: AppConfig.isProduction ? 90 : 20,
              ),
              sendTimeout: Duration(seconds: AppConfig.isProduction ? 30 : 20),
              contentType: Headers.jsonContentType,
              responseType: ResponseType.json,
            ),
          ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _tokenStorage.read();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  final TokenStorage _tokenStorage;
  final Dio _dio;

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      return (await _dio.get<dynamic>(
        path,
        queryParameters: queryParameters,
      )).data;
    } on DioException catch (error) {
      throw AppException.fromDio(error);
    }
  }

  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? headers,
  }) async {
    try {
      return (await _dio.post<dynamic>(
        path,
        data: data,
        options: Options(headers: headers),
      )).data;
    } on DioException catch (error) {
      throw AppException.fromDio(error);
    }
  }
}
