import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/widgets.dart';
import '../../l10n/l10n.dart';
import 'appointment_providers.dart';

class AppointmentsScreen extends ConsumerStatefulWidget {
  const AppointmentsScreen({super.key});

  @override
  ConsumerState<AppointmentsScreen> createState() => _AppointmentsScreenState();
}

class _AppointmentsScreenState extends ConsumerState<AppointmentsScreen> {
  String _view = 'upcoming';

  @override
  Widget build(BuildContext context) {
    final appointments = ref.watch(appointmentsProvider(_view));
    final views = {
      'upcoming': context.l10n.upcoming,
      'past': context.l10n.past,
      'cancelled': context.l10n.cancelled,
      'all': context.l10n.all,
    };
    return Scaffold(
      appBar: AppBar(
        title: Text(context.l10n.myAppointments),
        actions: [
          IconButton(
            tooltip: context.l10n.newAppointment,
            onPressed: () => context.push('/book'),
            icon: const Icon(Icons.add_rounded),
          ),
        ],
      ),
      body: Column(
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              children: views.entries
                  .map(
                    (entry) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(entry.value),
                        selected: _view == entry.key,
                        onSelected: (_) => setState(() => _view = entry.key),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
          Expanded(
            child: appointments.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => ErrorState(
                error: error,
                onRetry: () => ref.invalidate(appointmentsProvider(_view)),
              ),
              data: (items) => RefreshIndicator(
                onRefresh: () =>
                    ref.refresh(appointmentsProvider(_view).future),
                child: items.isEmpty
                    ? ListView(
                        children: [
                          EmptyState(
                            icon: Icons.event_busy_outlined,
                            title: switch (_view) {
                              'upcoming' => context.l10n.noUpcomingSection,
                              'past' => context.l10n.noPastSection,
                              'cancelled' => context.l10n.noCancelledSection,
                              _ => context.l10n.noAllSection,
                            },
                            message: _view == 'upcoming'
                                ? context.l10n.bookServiceEmptyHint
                                : context.l10n.noAppointmentsInSection,
                            action: _view == 'upcoming'
                                ? FilledButton(
                                    onPressed: () => context.push('/book'),
                                    child: Text(context.l10n.bookNow),
                                  )
                                : null,
                          ),
                        ],
                      )
                    : Align(
                        alignment: Alignment.topCenter,
                        child: ListView.builder(
                          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                          itemCount: items.length,
                          itemBuilder: (context, index) => ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 720),
                            child: AppointmentCard(
                              appointment: items[index],
                              onTap: () => context.push(
                                '/appointments/${items[index].id}',
                              ),
                              reviewActionLabel:
                                  items[index].status == 'COMPLETED'
                                  ? (items[index].reviewId == null
                                        ? context.l10n.leaveReview
                                        : context.l10n.yourReview)
                                  : null,
                              onReview: items[index].status == 'COMPLETED'
                                  ? () => context.push(
                                      '/appointments/${items[index].id}/review'
                                      '${items[index].reviewId == null ? '' : '?reviewId=${items[index].reviewId}'}',
                                    )
                                  : null,
                            ),
                          ),
                        ),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
