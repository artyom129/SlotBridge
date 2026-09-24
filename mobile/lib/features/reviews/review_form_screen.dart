import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/providers.dart';
import '../../core/ui/widgets.dart';
import '../../domain/models.dart';
import '../../features/appointments/appointment_providers.dart';
import '../../l10n/l10n.dart';

class ReviewFormScreen extends ConsumerStatefulWidget {
  const ReviewFormScreen({
    super.key,
    required this.appointmentId,
    this.reviewId,
  });

  final String appointmentId;
  final String? reviewId;

  @override
  ConsumerState<ReviewFormScreen> createState() => _ReviewFormScreenState();
}

class _ReviewFormScreenState extends ConsumerState<ReviewFormScreen> {
  final _comment = TextEditingController();
  int _overall = 0;
  int? _quality;
  int? _service;
  int? _punctuality;
  bool _anonymous = false;
  bool _canEdit = true;
  bool _loading = false;
  bool _initialLoading = false;
  Object? _error;
  Review? _saved;

  bool get _editing => widget.reviewId != null;

  @override
  void initState() {
    super.initState();
    if (_editing) _load();
  }

  Future<void> _load() async {
    setState(() => _initialLoading = true);
    try {
      final review = await ref
          .read(reviewRepositoryProvider)
          .get(widget.reviewId!);
      if (!mounted) return;
      setState(() {
        _overall = review.overallRating;
        _quality = review.qualityRating;
        _service = review.serviceRating;
        _punctuality = review.punctualityRating;
        _anonymous = review.isAnonymous;
        _canEdit = review.canEdit;
        _comment.text = review.comment ?? '';
      });
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _initialLoading = false);
    }
  }

  Future<void> _submit() async {
    if (_overall == 0 || _loading || !_canEdit) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repository = ref.read(reviewRepositoryProvider);
      final review = _editing
          ? await repository.update(
              widget.reviewId!,
              overallRating: _overall,
              qualityRating: _quality,
              serviceRating: _service,
              punctualityRating: _punctuality,
              comment: _comment.text,
              isAnonymous: _anonymous,
            )
          : await repository.create(
              appointmentId: widget.appointmentId,
              overallRating: _overall,
              qualityRating: _quality,
              serviceRating: _service,
              punctualityRating: _punctuality,
              comment: _comment.text,
              isAnonymous: _anonymous,
            );
      for (final view in const ['all', 'upcoming', 'past', 'cancelled']) {
        ref.invalidate(appointmentsProvider(view));
      }
      ref.invalidate(appointmentDetailProvider(widget.appointmentId));
      if (mounted) setState(() => _saved = review);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openExternalReview(String value) async {
    final uri = Uri.tryParse(value);
    if (uri == null || uri.scheme != 'https') return;
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) &&
        mounted) {
      setState(
        () => _error = StateError('Could not open external review page'),
      );
    }
  }

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_initialLoading) {
      return Scaffold(
        appBar: AppBar(title: Text(context.l10n.yourReview)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (_saved != null) return _success(context, _saved!);
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _editing ? context.l10n.yourReview : context.l10n.rateSpecialist,
        ),
      ),
      body: PageBody(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              context.l10n.reviewOverall,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Center(
              child: StarRating(
                key: const Key('overallRating'),
                value: _overall,
                enabled: !_loading && _canEdit,
                onChanged: (value) => setState(() => _overall = value),
                size: 42,
              ),
            ),
            const SizedBox(height: 22),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  children: [
                    _CriterionRating(
                      label: context.l10n.reviewQuality,
                      value: _quality,
                      enabled: !_loading && _canEdit,
                      onChanged: (value) => setState(() => _quality = value),
                    ),
                    _CriterionRating(
                      label: context.l10n.reviewService,
                      value: _service,
                      enabled: !_loading && _canEdit,
                      onChanged: (value) => setState(() => _service = value),
                    ),
                    _CriterionRating(
                      label: context.l10n.reviewPunctuality,
                      value: _punctuality,
                      enabled: !_loading && _canEdit,
                      onChanged: (value) =>
                          setState(() => _punctuality = value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('reviewComment'),
              controller: _comment,
              enabled: !_loading && _canEdit,
              maxLength: 5000,
              minLines: 4,
              maxLines: 8,
              decoration: InputDecoration(
                labelText: context.l10n.reviewComment,
                alignLabelWithHint: true,
              ),
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: Text(context.l10n.reviewAnonymous),
              subtitle: Text(context.l10n.reviewAnonymousHint),
              value: _anonymous,
              onChanged: _loading || !_canEdit
                  ? null
                  : (value) => setState(() => _anonymous = value),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                readableError(context, _error!),
                textAlign: TextAlign.center,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            if (_editing && !_canEdit) ...[
              const SizedBox(height: 8),
              Text(
                context.l10n.reviewEditExpired,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: 18),
            FilledButton.icon(
              key: const Key('publishReviewButton'),
              onPressed: _overall == 0 || _loading || !_canEdit
                  ? null
                  : _submit,
              icon: _loading
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send_rounded),
              label: Text(
                _loading
                    ? context.l10n.reviewPublishing
                    : context.l10n.reviewPublish,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _success(BuildContext context, Review review) {
    final externalUrl = review.externalReviewUrl2gis;
    final suggestExternal =
        review.overallRating >= 4 &&
        externalUrl != null &&
        externalUrl.isNotEmpty;
    return Scaffold(
      appBar: AppBar(title: Text(context.l10n.reviewPublished)),
      body: PageBody(
        child: Column(
          children: [
            const Icon(
              Icons.check_circle_rounded,
              size: 80,
              color: Colors.green,
            ),
            const SizedBox(height: 18),
            Text(
              context.l10n.reviewThankYou,
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            if (suggestExternal) ...[
              const SizedBox(height: 22),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    children: [
                      Text(
                        context.l10n.review2gisPrompt,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: () => _openExternalReview(externalUrl),
                        icon: const Icon(Icons.open_in_new_rounded),
                        label: Text(context.l10n.review2gisOpen),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton(
              onPressed: () => context.pop(),
              child: Text(context.l10n.backToAppointment),
            ),
          ],
        ),
      ),
    );
  }
}

class StarRating extends StatelessWidget {
  const StarRating({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
    this.size = 28,
  });

  final int value;
  final ValueChanged<int> onChanged;
  final bool enabled;
  final double size;

  @override
  Widget build(BuildContext context) => Semantics(
    label: context.l10n.reviewStars(value),
    child: Wrap(
      alignment: WrapAlignment.center,
      children: List.generate(
        5,
        (index) => IconButton(
          key: Key('reviewStar${index + 1}'),
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          onPressed: enabled ? () => onChanged(index + 1) : null,
          iconSize: size,
          color: Theme.of(context).colorScheme.primary,
          icon: Icon(
            index < value ? Icons.star_rounded : Icons.star_outline_rounded,
          ),
        ),
      ),
    ),
  );
}

class _CriterionRating extends StatelessWidget {
  const _CriterionRating({
    required this.label,
    required this.value,
    required this.enabled,
    required this.onChanged,
  });
  final String label;
  final int? value;
  final bool enabled;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      children: [
        Expanded(child: Text(label)),
        DropdownButton<int>(
          value: value,
          hint: const Text('—'),
          items: List.generate(
            5,
            (index) => DropdownMenuItem(
              value: index + 1,
              child: Text('${index + 1} ★'),
            ),
          ),
          onChanged: enabled ? (item) => onChanged(item!) : null,
        ),
      ],
    ),
  );
}
