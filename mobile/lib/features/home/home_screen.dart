import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../l10n/l10n.dart';
import '../appointments/appointment_providers.dart';
import '../auth/auth_controller.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).value;
    final upcoming = ref.watch(appointmentsProvider('upcoming'));
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
