import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../domain/models.dart';

final authControllerProvider = AsyncNotifierProvider<AuthController, AppUser?>(
  AuthController.new,
);

class AuthController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final repository = ref.read(authRepositoryProvider);
    if (!await repository.hasSession()) {
      return null;
    }
    try {
      final user = await repository.currentUser();
      if (user.role != 'CLIENT') {
        await repository.logout();
        return null;
      }
      return user;
    } catch (_) {
      await repository.logout();
      return null;
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).login(email, password),
    );
  }

  Future<void> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
    String? phone,
  }) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(authRepositoryProvider)
          .register(
            firstName: firstName,
            lastName: lastName,
            email: email,
            password: password,
            phone: phone,
          ),
    );
  }

  void clearError() {
    if (state.hasError) {
      state = const AsyncData(null);
    }
  }

  Future<void> updateProfile({
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    final previous = state.value;
    try {
      final updated = await ref
          .read(authRepositoryProvider)
          .updateProfile(
            firstName: firstName,
            lastName: lastName,
            phone: phone,
          );
      state = AsyncData(updated);
    } catch (error, stackTrace) {
      state = AsyncData(previous);
      Error.throwWithStackTrace(error, stackTrace);
    }
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const AsyncData(null);
  }
}
