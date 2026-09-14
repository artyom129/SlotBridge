import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../domain/models.dart';

final appointmentsProvider = FutureProvider.family<List<Appointment>, String>(
  (ref, view) => ref.watch(bookingRepositoryProvider).list(view: view),
);

final appointmentDetailProvider = FutureProvider.family<Appointment, String>(
  (ref, id) => ref.watch(bookingRepositoryProvider).detail(id),
);
