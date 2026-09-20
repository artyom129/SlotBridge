import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/ui/widgets.dart';
import '../../data/journey_repository.dart';
import '../../domain/models.dart';
import 'journey_controller.dart';

class JourneyScreen extends ConsumerStatefulWidget {
  const JourneyScreen({super.key});

  @override
  ConsumerState<JourneyScreen> createState() => _JourneyScreenState();
}

class _JourneyScreenState extends ConsumerState<JourneyScreen> {
  bool get _en => Localizations.localeOf(context).languageCode == 'en';

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      final controller = ref.read(journeyControllerProvider.notifier);
      controller.reset();
      controller.load();
    });
  }

  Future<void> _pickDate(JourneyState state) async {
    final date = await showDatePicker(
      context: context,
      initialDate: state.date ?? DateTime.now().add(const Duration(days: 1)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 90)),
    );
    if (date != null) {
      ref.read(journeyControllerProvider.notifier).setDate(date);
    }
  }

  Future<void> _pickTime(JourneyState state, {required bool start}) async {
    final current = start ? state.after : state.before;
    final value = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: current.hour, minute: current.minute),
    );
    if (value == null) return;
    final converted = TimeOfDayValue(value.hour, value.minute);
    ref
        .read(journeyControllerProvider.notifier)
        .setTimes(
          start ? converted : state.after,
          start ? state.before : converted,
        );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(journeyControllerProvider);
    final validTimeRange =
        state.after.hour * 60 + state.after.minute <
        state.before.hour * 60 + state.before.minute;
    return Scaffold(
      appBar: AppBar(title: Text(_en ? 'Smart Journey' : 'Умный маршрут')),
      body: PageBody(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _en
                  ? 'Choose services for one visit'
                  : 'Выберите услуги на один визит',
              style: Theme.of(context).textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            Text(
              _en
                  ? 'SlotBridge will find real consecutive slots with minimum waiting.'
                  : 'SlotBridge найдёт реальные последовательные слоты с минимальным ожиданием.',
            ),
            const SizedBox(height: 20),
            if (state.loading && state.catalog == null)
              const Center(child: CircularProgressIndicator())
            else if (state.catalog == null && state.error != null)
              ErrorState(
                error: state.error!,
                onRetry: () =>
                    ref.read(journeyControllerProvider.notifier).load(),
              )
            else if (state.catalog != null) ...[
              ...state.catalog!.services.map((service) {
                final selectedIndex = state.selectedServices.indexWhere(
                  (selected) => selected.id == service.id,
                );
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: CheckboxListTile(
                    key: ValueKey('journey-service-${service.id}'),
                    value: state.selectedServices.any(
                      (selected) => selected.id == service.id,
                    ),
                    onChanged: state.submitting
                        ? null
                        : (_) => ref
                              .read(journeyControllerProvider.notifier)
                              .toggleService(service),
                    title: Text(
                      service.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    subtitle: Text(
                      _en
                          ? '${service.durationMinutes} min'
                          : '${service.durationMinutes} мин',
                    ),
                    secondary: selectedIndex < 0
                        ? const Icon(Icons.spa_outlined)
                        : CircleAvatar(
                            radius: 16,
                            child: Text('${selectedIndex + 1}'),
                          ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    tileColor: Theme.of(context)
                        .colorScheme
                        .surfaceContainerLow,
                    controlAffinity: ListTileControlAffinity.trailing,
                  ),
                );
              }),
              const SizedBox(height: 12),
              Card(
                child: Column(
                  children: [
                    ListTile(
                      minVerticalPadding: 14,
                      leading: const Icon(Icons.calendar_today_outlined),
                      title: Text(_en ? 'Visit date' : 'Дата визита'),
                      subtitle: Text(
                        state.date == null
                            ? (_en ? 'Choose a date' : 'Выберите дату')
                            : DateFormat.yMMMMd(
                                Localizations.localeOf(context).languageCode,
                              ).format(state.date!),
                      ),
                      onTap: state.submitting ? null : () => _pickDate(state),
                    ),
                    const Divider(height: 1),
                    Row(
                      children: [
                        Expanded(
                          child: ListTile(
                            key: const Key('journeyAfterTime'),
                            title: Text(_en ? 'After' : 'После'),
                            subtitle: Text(state.after.apiValue),
                            onTap: state.submitting
                                ? null
                                : () => _pickTime(state, start: true),
                          ),
                        ),
                        Expanded(
                          child: ListTile(
                            key: const Key('journeyBeforeTime'),
                            title: Text(_en ? 'Finish by' : 'Закончить до'),
                            subtitle: Text(state.before.apiValue),
                            onTap: state.submitting
                                ? null
                                : () => _pickTime(state, start: false),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (!validTimeRange) ...[
                Text(
                  _en
                      ? 'The finish time must be later than the start time.'
                      : 'Время окончания должно быть позже времени начала.',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 10),
              ],
              FilledButton.icon(
                key: const Key('planJourneyButton'),
                onPressed:
                    state.selectedServices.length >= 2 &&
                        validTimeRange &&
                        !state.loading &&
                        !state.submitting
                    ? () => ref.read(journeyControllerProvider.notifier).plan()
                    : null,
                icon: state.loading
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.route_rounded),
                label: Text(
                  state.loading
                      ? (_en ? 'Building routes…' : 'Строим маршруты…')
                      : (_en ? 'Find routes' : 'Найти маршруты'),
                ),
              ),
              if (state.conflict) ...[
                const SizedBox(height: 16),
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      _en
                          ? 'One slot was taken. The whole route was not booked; fresh alternatives are shown below.'
                          : 'Один слот уже занят. Маршрут не был записан частично — ниже новые варианты.',
                    ),
                  ),
                ),
              ],
              if (state.error != null && !state.conflict) ...[
                const SizedBox(height: 16),
                ErrorState(
                  error: state.error!,
                  onRetry: () =>
                      ref.read(journeyControllerProvider.notifier).plan(),
                ),
              ],
              if (state.plan != null) ...[
                const SizedBox(height: 24),
                if (state.plan!.routes.isEmpty)
                  EmptyState(
                    icon: Icons.event_busy_outlined,
                    title: _en ? 'No complete route' : 'Нет полного маршрута',
                    message: _en
                        ? 'Change the date or time range and try again.'
                        : 'Измените дату или диапазон времени и повторите.',
                  )
                else
                  ...state.plan!.routes.map(
                    (route) => _JourneyRouteCard(
                      route: route,
                      submitting: state.submitting,
                      isEnglish: _en,
                      onChoose: () => _confirmAndBook(route),
                    ),
                  ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _confirmAndBook(JourneyRoute route) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_en ? 'Book this route?' : 'Записать этот маршрут?'),
        content: SingleChildScrollView(
          child: Text(
            _en
                ? '${route.steps.length} appointments will be created together. If one slot conflicts, none will be saved.'
                : 'Будут одновременно созданы записи: ${route.steps.length}. При конфликте одного слота не сохранится ни одна.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text(_en ? 'Back' : 'Назад'),
          ),
          FilledButton(
            key: const Key('confirmJourneyButton'),
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(_en ? 'Book route' : 'Записать маршрут'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final result = await ref
        .read(journeyControllerProvider.notifier)
        .book(route);
    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _en ? 'Journey booked successfully' : 'Маршрут успешно записан',
          ),
        ),
      );
      context.go('/appointments');
    }
  }
}

class _JourneyRouteCard extends StatelessWidget {
  const _JourneyRouteCard({
    required this.route,
    required this.submitting,
    required this.isEnglish,
    required this.onChoose,
  });

  final JourneyRoute route;
  final bool submitting;
  final bool isEnglish;
  final VoidCallback onChoose;

  String get title => switch (route.strategy) {
    'FASTEST' => isEnglish ? 'Fastest' : 'Быстрее всего',
    'EARLIEST' => isEnglish ? 'Earliest possible' : 'Как можно раньше',
    _ => isEnglish ? 'Fewer specialists' : 'Меньше сотрудников',
  };

  @override
  Widget build(BuildContext context) => Card(
    key: ValueKey('journey-route-${route.strategy}'),
    margin: const EdgeInsets.only(bottom: 14),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 12),
          ...route.steps.map(
            (step) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 92,
                    child: Text(
                      '${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(step.localStartsAt)}–'
                      '${DateFormat.Hm(Localizations.localeOf(context).languageCode).format(step.localEndsAt)}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          step.service.name,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        Text(
                          step.employee.name,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const Divider(),
          Wrap(
            spacing: 12,
            runSpacing: 6,
            children: [
              Text(
                isEnglish
                    ? 'Total: ${route.totalMinutes} min'
                    : 'Общее время: ${route.totalMinutes} мин',
              ),
              Text(
                isEnglish
                    ? 'Waiting: ${route.waitMinutes} min'
                    : 'Ожидание: ${route.waitMinutes} мин',
              ),
              Text(
                isEnglish
                    ? 'Specialists: ${route.employeeCount}'
                    : 'Сотрудников: ${route.employeeCount}',
              ),
            ],
          ),
          const SizedBox(height: 14),
          FilledButton(
            key: ValueKey('choose-journey-${route.strategy}'),
            onPressed: submitting ? null : onChoose,
            child: Text(
              submitting
                  ? (isEnglish ? 'Booking…' : 'Записываем…')
                  : (isEnglish ? 'Choose this route' : 'Выбрать этот маршрут'),
            ),
          ),
        ],
      ),
    ),
  );
}
