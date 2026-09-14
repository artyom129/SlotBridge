import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../core/ui/widgets.dart';
import '../../domain/models.dart';
import '../../l10n/l10n.dart';
import 'appointment_providers.dart';

class RescheduleScreen extends ConsumerStatefulWidget {
  const RescheduleScreen({super.key, required this.appointmentId});

  final String appointmentId;

  @override
  ConsumerState<RescheduleScreen> createState() => _RescheduleScreenState();
}

class _RescheduleScreenState extends ConsumerState<RescheduleScreen> {
  DateTime? _date;
  Availability? _availability;
  AvailabilitySlot? _slot;
  bool _loading = false;
  Object? _error;

  Future<void> _loadDate(Appointment appointment, DateTime date) async {
    setState(() {
      _date = date;
      _availability = null;
      _slot = null;
      _loading = true;
      _error = null;
    });
    try {
      final availability = await ref
          .read(bookingRepositoryProvider)
          .availability(
            branchId: appointment.branch.id,
            employeeId: appointment.employee.id,
            serviceId: appointment.service.id,
            date: date,
          );
      if (mounted) setState(() => _availability = availability);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirm() async {
    final slot = _slot;
    if (slot == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(bookingRepositoryProvider)
          .reschedule(
            widget.appointmentId,
            startsAt: slot.start,
            reason: 'Клиент перенёс запись в мобильном приложении',
          );
      for (final view in const ['all', 'upcoming', 'past', 'cancelled']) {
        ref.invalidate(appointmentsProvider(view));
      }
      ref.invalidate(appointmentDetailProvider(widget.appointmentId));
      if (mounted) Navigator.pop(context);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(appointmentDetailProvider(widget.appointmentId));
    return Scaffold(
      appBar: AppBar(title: Text(context.l10n.rescheduleTitle)),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorState(
          error: error,
          onRetry: () =>
              ref.invalidate(appointmentDetailProvider(widget.appointmentId)),
        ),
        data: (appointment) {
          final today = DateUtils.dateOnly(DateTime.now());
          return PageBody(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  context.l10n.chooseNewDate,
                  style: Theme.of(context).textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Text(
                  context.l10n.appointmentWithSpecialist(
                    appointment.service.name,
                    appointment.employee.name,
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(8),
                    child: CalendarDatePicker(
                      initialDate: today,
                      firstDate: today,
                      lastDate: today.add(const Duration(days: 90)),
                      onDateChanged: (date) => _loadDate(appointment, date),
                    ),
                  ),
                ),
                if (_loading) ...[
                  const SizedBox(height: 20),
                  const Center(child: CircularProgressIndicator()),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    readableError(context, _error!),
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                if (_availability != null) ...[
                  const SizedBox(height: 22),
                  Text(
                    _date == null
                        ? context.l10n.availableTimes
                        : context.l10n.availableTimesOnDate(
                            DateFormat('d MMM y', 'ru').format(_date!),
                          ),
                    style: Theme.of(context).textTheme.titleLarge
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 6),
                  Text(context.l10n.timesInTimezone(_availability!.timezone)),
                  const SizedBox(height: 12),
                  if (_availability!.slots.isEmpty)
                    Text(context.l10n.noAvailableTimes)
                  else
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: _availability!.slots
                          .map(
                            (slot) => ChoiceChip(
                              label: Text(
                                DateFormat.Hm('ru').format(slot.localStart),
                              ),
                              selected: _slot?.start == slot.start,
                              onSelected: (_) => setState(() => _slot = slot),
                            ),
                          )
                          .toList(),
                    ),
                ],
                if (_slot != null) ...[
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    key: const Key('confirmRescheduleButton'),
                    onPressed: _loading ? null : _confirm,
                    icon: const Icon(Icons.check_rounded),
                    label: Text(context.l10n.confirmNewTime),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}
