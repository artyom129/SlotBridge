import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/appointments/appointment_detail_screen.dart';
import '../../features/appointments/appointments_screen.dart';
import '../../features/appointments/reschedule_screen.dart';
import '../../features/auth/auth_controller.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/auth/splash_screen.dart';
import '../../features/booking/booking_flow_screen.dart';
import '../../features/ai/ai_assistant_screen.dart';
import '../../features/home/app_shell.dart';
import '../../features/home/home_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../l10n/l10n.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authControllerProvider);
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final location = state.matchedLocation;
      final isLogin = location == '/login';
      final isRegister = location == '/register';
      final isSplash = location == '/splash';
      final isAuthRoute = isLogin || isRegister;
      if (auth.isLoading) {
        return isAuthRoute ? null : (isSplash ? null : '/splash');
      }
      final signedIn = auth.value != null;
      if (!signedIn) return isAuthRoute ? null : '/login';
      if (isAuthRoute || isSplash) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) =>
            AppShell(location: state.uri.path, child: child),
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            path: '/appointments',
            builder: (context, state) => const AppointmentsScreen(),
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/book',
        builder: (context, state) => const BookingFlowScreen(),
      ),
      GoRoute(
        path: '/ai',
        builder: (context, state) => const AiAssistantScreen(),
      ),
      GoRoute(
        path: '/appointments/:id/reschedule',
        builder: (context, state) =>
            RescheduleScreen(appointmentId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/appointments/:id',
        builder: (context, state) => AppointmentDetailScreen(
          appointmentId: state.pathParameters['id']!,
          justCreated: state.uri.queryParameters['created'] == 'true',
        ),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: Text(context.l10n.appTitle)),
      body: Center(
        child: FilledButton(
          onPressed: () => context.go('/home'),
          child: Text(context.l10n.returnHome),
        ),
      ),
    ),
  );
});
