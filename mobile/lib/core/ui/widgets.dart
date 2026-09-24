import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../errors/app_exception.dart';
import '../../domain/models.dart';
import '../../l10n/app_localizations.dart';
import '../../l10n/l10n.dart';

String readableError(BuildContext context, Object error) {
  final l10n = context.l10n;
  if (error is! AppException) return l10n.errorGeneric;

  switch (error.code) {
    case 'timeout':
      return l10n.errorTimeout;
    case 'connection_error':
      return l10n.errorConnection;
    case 'SLOT_ALREADY_BOOKED':
      return l10n.errorSlotUnavailable;
    case 'BOOKING_SCOPE_NOT_FOUND':
      return l10n.errorBookingScope;
    case 'RESOURCE_NOT_FOUND':
    case 'SCHEDULE_RESOURCE_NOT_FOUND':
      return l10n.errorNotFound;
    case 'client_only':
      return l10n.errorClientOnly;
    case 'no_active_location':
      return l10n.errorNoActiveLocation;
    case 'registration_login_failed':
      return l10n.accountCreatedLogin;
    case 'APPOINTMENT_NOT_COMPLETED':
      return l10n.reviewAppointmentNotCompleted;
    case 'REVIEW_ALREADY_EXISTS':
      return l10n.reviewAlreadyExists;
    case 'REVIEW_EDIT_WINDOW_EXPIRED':
      return l10n.reviewEditExpired;
  }

  switch (error.statusCode) {
    case 401:
      return l10n.errorInvalidCredentials;
    case 403:
      return l10n.errorAccessDenied;
    case 404:
      return l10n.errorNotFound;
    case 409:
      return l10n.errorConflict;
    case 422:
      return l10n.errorCheckData;
  }

  final message = error.message.toLowerCase();
  if (message.contains('invalid email or password')) {
    return l10n.errorInvalidCredentials;
  }
  if (message.contains('cannot reach') || message.contains('connection')) {
    return l10n.errorConnection;
  }
  if (message.contains('too long') || message.contains('timeout')) {
    return l10n.errorTimeout;
  }
  return l10n.errorGeneric;
}

String appointmentStatusLabel(AppLocalizations l10n, String status) {
  return switch (status) {
    'BOOKED' => l10n.statusBooked,
    'CONFIRMED' => l10n.statusConfirmed,
    'IN_PROGRESS' => l10n.statusInProgress,
    'COMPLETED' => l10n.statusCompleted,
    'CANCELLED' => l10n.statusCancelled,
    'NO_SHOW' => l10n.statusNoShow,
    _ => l10n.statusUnknown,
  };
}

class PageBody extends StatelessWidget {
  const PageBody({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Align(
        alignment: Alignment.topCenter,
        child: SingleChildScrollView(
          padding: padding,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: child,
          ),
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 16),
      child: Column(
        children: [
          Icon(icon, size: 52, color: Theme.of(context).colorScheme.primary),
          const SizedBox(height: 16),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(message, textAlign: TextAlign.center),
          if (action != null) ...[const SizedBox(height: 20), action!],
        ],
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.error, required this.onRetry});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => EmptyState(
    icon: Icons.cloud_off_rounded,
    title: context.l10n.errorCouldNotLoadData,
    message: readableError(context, error),
    action: FilledButton.tonal(
      onPressed: onRetry,
      child: Text(context.l10n.tryAgain),
    ),
  );
}

class StatusBadge extends StatelessWidget {
  const StatusBadge(this.status, {super.key});

  final String status;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final color = switch (status) {
      'BOOKED' => Colors.blue,
      'CONFIRMED' => Colors.teal,
      'IN_PROGRESS' => Colors.deepPurple,
      'COMPLETED' => Colors.green,
      'CANCELLED' => Colors.red,
      'NO_SHOW' => Colors.orange,
      _ => Colors.grey,
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        child: Text(
          appointmentStatusLabel(context.l10n, status),
          style: TextStyle(
            color: isDark ? color.shade200 : color.shade700,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class AppointmentCard extends StatelessWidget {
  const AppointmentCard({
    super.key,
    required this.appointment,
    required this.onTap,
    this.reviewActionLabel,
    this.onReview,
  });

  final Appointment appointment;
  final VoidCallback onTap;
  final String? reviewActionLabel;
  final VoidCallback? onReview;

  @override
  Widget build(BuildContext context) {
    final start = appointment.localStartsAt;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    width: 54,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      children: [
                        Text(
                          DateFormat.MMM(
                            Localizations.localeOf(context).languageCode,
                          ).format(start).toUpperCase(),
                          style: const TextStyle(fontSize: 11),
                        ),
                        Text(
                          '${start.day}',
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                appointment.service.name,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ),
                            StatusBadge(appointment.status),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(start)} · ${appointment.employee.name}',
                        ),
                        Text(
                          appointment.branch.name,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded),
                ],
              ),
              if (reviewActionLabel != null && onReview != null) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: onReview,
                  icon: const Icon(Icons.star_outline_rounded),
                  label: Text(reviewActionLabel!),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
