import '../core/errors/app_exception.dart';
import '../core/network/api_client.dart';
import '../core/storage/token_storage.dart';
import '../domain/models.dart';

abstract interface class AuthRepository {
  Future<AppUser> login(String email, String password);
  Future<AppUser> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  });
  Future<AppUser> currentUser();
  Future<AppUser> updateProfile({
    required String firstName,
    required String lastName,
    String? phone,
  });
  Future<void> logout();
  Future<bool> hasSession();
}

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._api, this._storage);

  final ApiClient _api;
  final TokenStorage _storage;

  @override
  Future<bool> hasSession() async =>
      (await _storage.read())?.isNotEmpty ?? false;

  @override
  Future<AppUser> login(String email, String password) async {
    final response = await _api.post(
      '/auth/login',
      data: {'email': email.trim().toLowerCase(), 'password': password},
    );
    final token = (response as JsonMap)['access_token'] as String;
    await _storage.write(token);
    try {
      final user = await currentUser();
      if (user.role != 'CLIENT') {
        throw const AppException(
          'Мобильное приложение предназначено для клиентов.',
          code: 'client_only',
        );
      }
      return user;
    } catch (_) {
      await _storage.clear();
      rethrow;
    }
  }

  @override
  Future<AppUser> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  }) async {
    final normalizedPhone = phone?.trim();
    await _api.post(
      '/auth/register',
      data: {
        'first_name': firstName.trim(),
        'last_name': lastName.trim(),
        'email': email.trim().toLowerCase(),
        'password': password,
        if (normalizedPhone != null && normalizedPhone.isNotEmpty)
          'phone': normalizedPhone,
      },
    );
    try {
      return await login(email, password);
    } catch (_) {
      throw const AppException(
        'Аккаунт создан. Теперь войдите.',
        code: 'registration_login_failed',
      );
    }
  }

  @override
  Future<AppUser> currentUser() async {
    final response = await _api.get('/auth/me');
    return AppUser.fromJson(response as JsonMap);
  }

  @override
  Future<AppUser> updateProfile({
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    final response = await _api.patch(
      '/auth/me',
      data: {
        'first_name': firstName.trim(),
        'last_name': lastName.trim(),
        'phone': phone?.trim(),
      },
    );
    return AppUser.fromJson(response as JsonMap);
  }

  @override
  Future<void> logout() => _storage.clear();
}
