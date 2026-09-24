import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../core/ui/widgets.dart';
import '../../domain/models.dart';
import '../../l10n/l10n.dart';
import 'appointment_providers.dart';

class AppointmentDetailScreen extends ConsumerStatefulWidget {
  const AppointmentDetailScreen({
    super.key,
    required this.appointmentId,
    this.justCreated = false,
  });

  final String appointmentId;
  final bool justCreated;

  @override
  ConsumerState<AppointmentDetailScreen> createState() =>
      _AppointmentDetailScreenState();
}

class _AppointmentDetailScreenState
    extends ConsumerState<AppointmentDetailScreen> {
  bool _isMutating = false;
  Object? _mutationError;

  Future<void> _cancel() async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.cancelAppointmentQuestion),
        content: TextField(
          controller: reasonController,
          maxLength: 500,
          decoration: InputDecoration(labelText: context.l10n.reasonOptional),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.l10n.keepAppointment),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.l10n.cancelAppointment),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) {
      reasonController.dispose();
      return;
    }
    setState(() {
      _isMutating = true;
      _mutationError = null;
    });
    try {
      await ref
          .read(bookingRepositoryProvider)
          .cancel(widget.appointmentId, reason: reasonController.text);
      for (final view in const ['all', 'upcoming', 'past', 'cancelled']) {
        ref.invalidate(appointmentsProvider(view));
      }
      ref.invalidate(appointmentDetailProvider(widget.appointmentId));
    } catch (error) {
      if (mounted) setState(() => _mutationError = error);
    } finally {
      reasonController.dispose();
      if (mounted) setState(() => _isMutating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(appointmentDetailProvider(widget.appointmentId));
    return Scaffold(
      appBar: AppBar(title: Text(context.l10n.appointmentDetails)),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorState(
          error: error,
          onRetry: () =>
              ref.invalidate(appointmentDetailProvider(widget.appointmentId)),
        ),
        data: (appointment) => PageBody(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.justCreated) ...[
                Card(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: ListTile(
                    leading: const Icon(Icons.check_circle_rounded),
                    title: Text(context.l10n.appointmentBooked),
                    subtitle: Text(context.l10n.slotConfirmed),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton(
                        onPressed: () => context.go('/appointments'),
                        child: Text(context.l10n.myAppointments),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => context.go('/home'),
                        child: Text(context.l10n.navHome),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
              ],
              _AppointmentHero(appointment: appointment),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      _DetailRow(
                        icon: Icons.person_outline_rounded,
                        label: context.l10n.specialistLabel,
                        value: appointment.employee.name,
                      ),
                      _DetailRow(
                        icon: Icons.place_outlined,
                        label: context.l10n.locationLabel,
                        value: appointment.branch.name,
                      ),
                      _DetailRow(
                        icon: Icons.public_rounded,
                        label: context.l10n.timezoneLabel,
                        value: appointment.timezone,
                      ),
                      if (appointment.clientNote != null)
                        _DetailRow(
                          icon: Icons.notes_rounded,
                          label: context.l10n.yourNote,
                          value: appointment.clientNote!,
                        ),
                      if (appointment.cancellationReason != null)
                        _DetailRow(
                          icon: Icons.info_outline_rounded,
                          label: context.l10n.cancellationReason,
                          value: appointment.cancellationReason!,
                          isLast: true,
                        ),
                    ],
                  ),
                ),
              ),
              if (_mutationError != null) ...[
                const SizedBox(height: 12),
                Text(
                  readableError(context, _mutationError!),
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (appointment.canClientChange) ...[
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _isMutating
                      ? null
                      : () => context.push(
                          '/appointments/${appointment.id}/reschedule',
                        ),
                  icon: const Icon(Icons.edit_calendar_rounded),
                  label: Text(context.l10n.reschedule),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  key: const Key('cancelAppointmentButton'),
                  onPressed: _isMutating ? null : _cancel,
                  icon: const Icon(Icons.cancel_outlined),
                  label: Text(
                    _isMutating
                        ? context.l10n.updating
                        : context.l10n.cancelAppointment,
                  ),
                ),
              ],
              if (appointment.status == 'COMPLETED') ...[
                const SizedBox(height: 16),
                FilledButton.icon(
                  key: const Key('reviewAppointmentButton'),
                  onPressed: () => context.push(
                    '/appointments/${appointment.id}/review'
                    '${appointment.reviewId == null ? '' : '?reviewId=${appointment.reviewId}'}',
                  ),
                  icon: Icon(
                    appointment.reviewId == null
                        ? Icons.star_outline_rounded
                        : Icons.rate_review_outlined,
                  ),
                  label: Text(
                    appointment.reviewId == null
                        ? context.l10n.leaveReview
                        : context.l10n.yourReview,
                  ),
                ),
              ],
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => context.push(
                  '/employees/${appointment.employee.id}/reviews'
                  '?name=${Uri.encodeQueryComponent(appointment.employee.name)}',
                ),
                icon: const Icon(Icons.reviews_outlined),
                label: Text(context.l10n.specialistReviews),
              ),
              if (appointment.history.isNotEmpty) ...[
                const SizedBox(height: 28),
                Text(
                  context.l10n.statusHistory,
                  style: Theme.of(context).textTheme.titleLarge
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                Card(
                  child: Column(
                    children: appointment.history
                        .map(
                          (item) => ListTile(
                            leading: const Icon(Icons.history_rounded),
                            title: Text(
                              appointmentStatusLabel(
                                context.l10n,
                                item.newStatus,
                              ),
                            ),
                            subtitle: Text(
                              [
                                DateFormat(
                                  'd MMM y, HH:mm',
                                  'ru',
                                ).format(item.createdAt.toLocal()),
                                if (item.reason != null) item.reason!,
                              ].join(' · '),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _AppointmentHero extends StatelessWidget {
  const _AppointmentHero({required this.appointment});

  final Appointment appointment;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  appointment.service.name,
                  style: Theme.of(context).textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              StatusBadge(appointment.status),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            DateFormat(
              'd MMMM, EEEE',
              Localizations.localeOf(context).languageCode,
            ).format(appointment.localStartsAt),
          ),
          const SizedBox(height: 4),
          Text(
            '${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(appointment.localStartsAt)} – ${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(appointment.localEndsAt)}',
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
        ],
      ),
    ),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
    this.isLast = false,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool isLast;

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.only(bottom: isLast ? 0 : 16),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              Text(value),
            ],
          ),
        ),
      ],
    ),
  );
}
