import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/ui/widgets.dart';
import '../../domain/models.dart';
import '../../l10n/l10n.dart';
import 'booking_controller.dart';

class BookingFlowScreen extends ConsumerStatefulWidget {
  const BookingFlowScreen({super.key});

  @override
  ConsumerState<BookingFlowScreen> createState() => _BookingFlowScreenState();
}

class _BookingFlowScreenState extends ConsumerState<BookingFlowScreen> {
  final _noteController = TextEditingController();

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(bookingControllerProvider.notifier).load());
  }

  @override
  void dispose() {
    ref.read(bookingControllerProvider.notifier).reset();
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(bookingControllerProvider);
    return PopScope(
      canPop: state.step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop && state.step > 0) {
          ref.read(bookingControllerProvider.notifier).back();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(context.l10n.bookAppointment),
          leading: IconButton(
            tooltip: context.l10n.back,
            onPressed: () {
              if (state.step > 0) {
                ref.read(bookingControllerProvider.notifier).back();
              } else {
                context.pop();
              }
            },
            icon: const Icon(Icons.arrow_back_rounded),
          ),
        ),
        body: PageBody(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _ProgressHeader(step: state.step),
              const SizedBox(height: 24),
              if (state.catalog != null)
                Text(
                  '${state.catalog!.organization.name} · ${state.catalog!.branch.name}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              const SizedBox(height: 8),
              if (state.isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 70),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (state.error != null && state.catalog == null)
                ErrorState(
                  error: state.error!,
                  onRetry: () =>
                      ref.read(bookingControllerProvider.notifier).load(),
                )
              else
                _StepContent(state: state, noteController: _noteController),
              if (state.error != null && state.catalog != null) ...[
                const SizedBox(height: 16),
                Semantics(
                  liveRegion: true,
                  child: Text(
                    readableError(context, state.error!),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                    textAlign: TextAlign.center,
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

class _ProgressHeader extends StatelessWidget {
  const _ProgressHeader({required this.step});

  final int step;

  @override
  Widget build(BuildContext context) {
    final titles = [
      context.l10n.bookingStepService,
      context.l10n.bookingStepSpecialist,
      context.l10n.bookingStepDate,
      context.l10n.bookingStepAvailability,
      context.l10n.bookingStepReview,
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                titles[step],
                style: Theme.of(context).textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
            ),
            Text('${step + 1} / ${titles.length}'),
          ],
        ),
        const SizedBox(height: 12),
        LinearProgressIndicator(
          value: (step + 1) / titles.length,
          minHeight: 7,
          borderRadius: BorderRadius.circular(99),
        ),
      ],
    );
  }
}

class _StepContent extends ConsumerWidget {
  const _StepContent({required this.state, required this.noteController});

  final BookingState state;
  final TextEditingController noteController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return switch (state.step) {
      0 => _ServiceStep(services: state.catalog?.services ?? const []),
      1 => _EmployeeStep(employees: state.employees),
      2 => const _DateStep(),
      3 => _AvailabilityStep(state: state),
      _ => _ReviewStep(state: state, noteController: noteController),
    };
  }
}

class _ServiceStep extends ConsumerWidget {
  const _ServiceStep({required this.services});

  final List<Service> services;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (services.isEmpty) {
      return EmptyState(
        icon: Icons.spa_outlined,
        title: context.l10n.noServices,
        message: context.l10n.locationHasNoServices,
      );
    }
    return Column(
      children: services
          .map(
            (service) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.all(18),
                  leading: CircleAvatar(
                    child: Text(
                      context.l10n.durationMinutes(service.durationMinutes),
                      style: const TextStyle(fontSize: 11),
                    ),
                  ),
                  title: Text(
                    service.name,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      [
                        service.description,
                        if (service.price != null)
                          '\$${service.price!.toStringAsFixed(2)}',
                      ].join(' · '),
                    ),
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => ref
                      .read(bookingControllerProvider.notifier)
                      .selectService(service),
                ),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _EmployeeStep extends ConsumerWidget {
  const _EmployeeStep({required this.employees});

  final List<Employee> employees;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (employees.isEmpty) {
      return EmptyState(
        icon: Icons.person_search_rounded,
        title: context.l10n.noSpecialist,
        message: context.l10n.noSpecialistForService,
      );
    }
    return Column(
      children: employees
          .map(
            (employee) => Card(
              child: ListTile(
                contentPadding: const EdgeInsets.all(18),
                leading: CircleAvatar(
                  child: Text(
                    employee.displayName.characters.first.toUpperCase(),
                  ),
                ),
                title: Text(
                  employee.displayName,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                subtitle: Text(context.l10n.availableSpecialist),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => ref
                    .read(bookingControllerProvider.notifier)
                    .selectEmployee(employee),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _DateStep extends ConsumerWidget {
  const _DateStep();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final today = DateUtils.dateOnly(DateTime.now());
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: CalendarDatePicker(
          initialDate: today,
          firstDate: today,
          lastDate: today.add(const Duration(days: 90)),
          onDateChanged: (date) =>
              ref.read(bookingControllerProvider.notifier).selectDate(date),
        ),
      ),
    );
  }
}

class _AvailabilityStep extends ConsumerWidget {
  const _AvailabilityStep({required this.state});

  final BookingState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final availability = state.availability;
    if (availability == null || availability.slots.isEmpty) {
      return EmptyState(
        icon: Icons.free_cancellation_outlined,
        title: context.l10n.noTimesOnDate,
        message: context.l10n.chooseAnotherDateHint,
        action: OutlinedButton(
          onPressed: () => ref.read(bookingControllerProvider.notifier).back(),
          child: Text(context.l10n.chooseAnotherDate),
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (state.error != null && state.slot != null) ...[
          FilledButton.icon(
            onPressed: () async {
              final ok = await ref
                  .read(bookingControllerProvider.notifier)
                  .joinWaitlist();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      ok
                          ? (Localizations.localeOf(context).languageCode ==
                                    'en'
                                ? 'Added to waitlist'
                                : 'Добавлено в лист ожидания')
                          : (Localizations.localeOf(context).languageCode ==
                                    'en'
                                ? 'Could not join waitlist'
                                : 'Не удалось добавить в лист ожидания'),
                    ),
                  ),
                );
              }
            },
            icon: const Icon(Icons.notifications_active_outlined),
            label: Text(
              Localizations.localeOf(context).languageCode == 'en'
                  ? 'Notify me if it becomes available'
                  : 'Сообщить, если освободится',
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (availability.recommendations.isNotEmpty) ...[
          Text(
            context.l10n.recommended,
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          ...availability.recommendations.map(
            (item) => Card(
              child: ListTile(
                leading: const Icon(Icons.star_rounded),
                title: Text(
                  DateFormat.Hm(Localizations.localeOf(context).languageCode)
                      .format(item.slot.localStart),
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text(switch (item.reason) {
                  'FILL_GAP' => context.l10n.fillsGap,
                  'EARLIEST' => context.l10n.earliestAvailable,
                  _ => context.l10n.bestOption,
                }),
                onTap: () => ref
                    .read(bookingControllerProvider.notifier)
                    .selectSlot(item.slot),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            context.l10n.allAvailableTimes,
            style: Theme.of(context).textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 10),
        ],
        Text(
          DateFormat(
            'd MMMM, EEEE',
            Localizations.localeOf(context).languageCode,
          ).format(state.date!),
          style: Theme.of(context).textTheme.titleMedium
              ?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text(context.l10n.timesInTimezone(availability.timezone)),
        const SizedBox(height: 18),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: availability.slots
              .map(
                (slot) => ActionChip(
                  key: ValueKey('slot-${slot.start.toIso8601String()}'),
                  avatar: const Icon(Icons.schedule_rounded, size: 18),
                  label: Text(
                    DateFormat.Hm(Localizations.localeOf(context).languageCode)
                        .format(slot.localStart),
                  ),
                  onPressed: () => ref
                      .read(bookingControllerProvider.notifier)
                      .selectSlot(slot),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

class _ReviewStep extends ConsumerWidget {
  const _ReviewStep({required this.state, required this.noteController});

  final BookingState state;
  final TextEditingController noteController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final slot = state.slot!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                _SummaryRow(
                  icon: Icons.spa_outlined,
                  label: context.l10n.serviceLabel,
                  value: state.service!.name,
                ),
                _SummaryRow(
                  icon: Icons.person_outline_rounded,
                  label: context.l10n.specialistLabel,
                  value: state.employee!.displayName,
                ),
                _SummaryRow(
                  icon: Icons.calendar_today_outlined,
                  label: context.l10n.dateLabel,
                  value: DateFormat(
                    'd MMMM y',
                    Localizations.localeOf(context).languageCode,
                  ).format(slot.localStart),
                ),
                _SummaryRow(
                  icon: Icons.schedule_rounded,
                  label: context.l10n.timeLabel,
                  value:
                      '${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(slot.localStart)} – ${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(slot.localEnd)}',
                ),
                _SummaryRow(
                  icon: Icons.place_outlined,
                  label: context.l10n.locationLabel,
                  value: state.catalog!.branch.name,
                  isLast: true,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: noteController,
          maxLength: 1000,
          minLines: 2,
          maxLines: 4,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(
            labelText: context.l10n.noteOptional,
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          key: const Key('confirmBookingButton'),
          onPressed: state.isSubmitting
              ? null
              : () async {
                  final appointment = await ref
                      .read(bookingControllerProvider.notifier)
                      .submit(noteController.text);
                  if (appointment != null && context.mounted) {
                    context.go('/appointments/${appointment.id}?created=true');
                  }
                },
          icon: state.isSubmitting
              ? const SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.check_rounded),
          label: Text(
            state.isSubmitting
                ? context.l10n.bookingInProgress
                : context.l10n.confirmBooking,
          ),
        ),
      ],
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({
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
      children: [
        Icon(icon, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ],
    ),
  );
}
