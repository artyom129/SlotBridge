import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../l10n/l10n.dart';
import '../appointments/appointment_providers.dart';
import '../auth/auth_controller.dart';
import '../../core/providers.dart';

import 'package:intl/intl.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  String? _acceptingWaitlistId;

  Future<void> _acceptWaitlist(String id) async {
    if (_acceptingWaitlistId != null) return;
    setState(() => _acceptingWaitlistId = id);
    try {
      await ref.read(waitlistRepositoryProvider).accept(id);
      ref.invalidate(waitlistProvider);
      ref.invalidate(appointmentsProvider('upcoming'));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              Localizations.localeOf(context).languageCode == 'en'
                  ? 'Appointment booked'
                  : 'Запись создана',
            ),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(readableError(context, error))));
      }
    } finally {
      if (mounted) setState(() => _acceptingWaitlistId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).value;
    final upcoming = ref.watch(appointmentsProvider('upcoming'));
    final waitlist = ref.watch(waitlistProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('SlotBridge'),
        actions: [
          IconButton(
            tooltip: context.l10n.refresh,
            onPressed: () => ref.invalidate(appointmentsProvider('upcoming')),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(appointmentsProvider('upcoming').future),
        child: PageBody(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                user == null
                    ? context.l10n.helloFallback
                    : context.l10n.helloUser(user.firstName),
                style: Theme.of(context).textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              Text(context.l10n.readyForVisit),
              const SizedBox(height: 22),
              waitlist.when(
                data: (items) {
                  final matched = items
                      .where(
                        (x) =>
                            x.status == 'MATCHED' && x.matchedStartsAt != null,
                      )
                      .firstOrNull;
                  if (matched == null) return const SizedBox.shrink();
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.notifications_active_rounded),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      Localizations.localeOf(context)
                                                  .languageCode ==
                                              'en'
                                          ? 'A time slot is available'
                                          : 'Освободилось время',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${matched.serviceName ?? ''}\n${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(matched.matchedStartsAt!.toLocal())} · ${matched.employeeName ?? ''}',
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Align(
                            alignment: Alignment.centerRight,
                            child: FilledButton.icon(
                              onPressed: _acceptingWaitlistId == null
                                  ? () => _acceptWaitlist(matched.id)
                                  : null,
                              icon: _acceptingWaitlistId == matched.id
                                  ? const SizedBox.square(
                                      dimension: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.check_rounded),
                              label: Text(
                                _acceptingWaitlistId == matched.id
                                    ? context.l10n.updating
                                    : context.l10n.bookNow,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
                loading: () => const SizedBox.shrink(),
                error: (_, _) => const SizedBox.shrink(),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Theme.of(context).colorScheme.primary,
                      Theme.of(context).colorScheme.tertiary,
                    ],
                  ),
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.auto_awesome_rounded, color: Colors.white),
                    const SizedBox(height: 24),
                    Text(
                      context.l10n.findConvenientTime,
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      context.l10n.chooseServiceSpecialistSlot,
                      style: const TextStyle(color: Colors.white),
                    ),
                    const SizedBox(height: 22),
                    FilledButton.icon(
                      key: const Key('startBookingButton'),
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: Theme.of(context).colorScheme.primary,
                      ),
                      onPressed: () => context.push('/book'),
                      icon: const Icon(Icons.add_rounded),
                      label: Text(context.l10n.bookAppointment),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.all(18),
                  leading: const CircleAvatar(
                    child: Icon(Icons.auto_awesome_rounded),
                  ),
                  title: const Text(
                    'SlotBridge AI',
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    Localizations.localeOf(context).languageCode == 'en'
                        ? 'Manage bookings with a message'
                        : 'Запишитесь обычным сообщением',
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push('/ai'),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      context.l10n.upcoming,
                      style: Theme.of(context).textTheme.titleLarge
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ),
                  TextButton(
                    onPressed: () => context.go('/appointments'),
                    child: Text(context.l10n.viewAll),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              upcoming.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (error, _) => ErrorState(
                  error: error,
                  onRetry: () =>
                      ref.invalidate(appointmentsProvider('upcoming')),
                ),
                data: (items) {
                  if (items.isEmpty) {
                    return EmptyState(
                      icon: Icons.event_available_rounded,
                      title: context.l10n.noUpcomingAppointments,
                      message: context.l10n.nextBookingAppearsHere,
                    );
                  }
                  return Column(
                    children: items
                        .take(3)
                        .map(
                          (item) => AppointmentCard(
                            appointment: item,
                            onTap: () =>
                                context.push('/appointments/${item.id}'),
                          ),
                        )
                        .toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
