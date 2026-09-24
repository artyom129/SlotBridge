import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../core/ui/widgets.dart';
import '../../domain/models.dart';
import '../../l10n/l10n.dart';

class EmployeeReviewsScreen extends ConsumerStatefulWidget {
  const EmployeeReviewsScreen({
    super.key,
    required this.employeeId,
    required this.employeeName,
  });
  final String employeeId;
  final String employeeName;

  @override
  ConsumerState<EmployeeReviewsScreen> createState() =>
      _EmployeeReviewsScreenState();
}

class _EmployeeReviewsScreenState extends ConsumerState<EmployeeReviewsScreen> {
  int? _filter;
  String _sort = 'newest';
  bool _loading = true;
  Object? _error;
  ReviewPage? _page;
  EmployeeRating? _rating;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repository = ref.read(reviewRepositoryProvider);
      final values = await Future.wait<Object>([
        repository.employeeReviews(
          widget.employeeId,
          rating: _filter,
          sort: _sort,
        ),
        repository.employeeRating(widget.employeeId),
      ]);
      if (!mounted) return;
      setState(() {
        _page = values[0] as ReviewPage;
        _rating = values[1] as EmployeeRating;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(context.l10n.specialistReviews)),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? ErrorState(error: _error!, onRetry: _load)
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
              children: [
                Text(
                  widget.employeeName,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                if (_rating != null) _RatingSummary(rating: _rating!),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilterChip(
                      label: Text(context.l10n.allRatings),
                      selected: _filter == null,
                      onSelected: (_) {
                        _filter = null;
                        _load();
                      },
                    ),
                    for (var star = 5; star >= 1; star--)
                      FilterChip(
                        label: Text('$star ★'),
                        selected: _filter == star,
                        onSelected: (_) {
                          _filter = star;
                          _load();
                        },
                      ),
                    DropdownButton<String>(
                      value: _sort,
                      items: [
                        DropdownMenuItem(
                          value: 'newest',
                          child: Text(context.l10n.sortNewest),
                        ),
                        DropdownMenuItem(
                          value: 'oldest',
                          child: Text(context.l10n.sortOldest),
                        ),
                        DropdownMenuItem(
                          value: 'highest_rating',
                          child: Text(context.l10n.sortHighest),
                        ),
                        DropdownMenuItem(
                          value: 'lowest_rating',
                          child: Text(context.l10n.sortLowest),
                        ),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        _sort = value;
                        _load();
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (_page!.items.isEmpty)
                  EmptyState(
                    icon: Icons.reviews_outlined,
                    title: context.l10n.noReviews,
                    message: context.l10n.noReviewsHint,
                  )
                else
                  ..._page!.items.map((review) => _ReviewCard(review: review)),
              ],
            ),
          ),
  );
}

class _RatingSummary extends StatelessWidget {
  const _RatingSummary({required this.rating});
  final EmployeeRating rating;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Text(
            rating.averageRating?.toStringAsFixed(1) ?? '—',
            style: Theme.of(context).textTheme.displaySmall,
          ),
          Text(context.l10n.reviewsCount(rating.reviewsCount)),
          const SizedBox(height: 10),
          for (var star = 5; star >= 1; star--)
            Row(
              children: [
                SizedBox(width: 30, child: Text('$star ★')),
                const SizedBox(width: 8),
                Expanded(
                  child: LinearProgressIndicator(
                    value: rating.reviewsCount == 0
                        ? 0
                        : (rating.distribution[star] ?? 0) /
                              rating.reviewsCount,
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 28,
                  child: Text('${rating.distribution[star] ?? 0}'),
                ),
              ],
            ),
        ],
      ),
    ),
  );
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({required this.review});
  final Review review;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  review.clientDisplayName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Text('${review.overallRating} ★'),
            ],
          ),
          Text(
            DateFormat.yMMMd(Localizations.localeOf(context).languageCode)
                .format(review.createdAt.toLocal()),
          ),
          if (review.comment != null) ...[
            const SizedBox(height: 10),
            Text(review.comment!),
          ],
          if (review.reply != null) ...[
            const SizedBox(height: 12),
            DecoratedBox(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      review.reply!.authorLabel,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    Text(review.reply!.text),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    ),
  );
}
