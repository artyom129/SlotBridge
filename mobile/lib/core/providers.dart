import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/auth_repository.dart';
import '../data/booking_repository.dart';
import '../data/catalog_repository.dart';
import '../data/waitlist_repository.dart';
import '../data/journey_repository.dart';
import 'network/api_client.dart';
import 'storage/token_storage.dart';

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => SecureTokenStorage(),
);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(ref.watch(tokenStorageProvider)),
);

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ApiAuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenStorageProvider),
  ),
);

final catalogRepositoryProvider = Provider<CatalogRepository>(
  (ref) => ApiCatalogRepository(ref.watch(apiClientProvider)),
);

final bookingRepositoryProvider = Provider<BookingRepository>(
  (ref) => ApiBookingRepository(ref.watch(apiClientProvider)),
);
final journeyRepositoryProvider = Provider<JourneyRepository>(
  (ref) => ApiJourneyRepository(ref.watch(apiClientProvider)),
);
final waitlistRepositoryProvider = Provider(
  (ref) => WaitlistRepository(ref.watch(apiClientProvider)),
);
final waitlistProvider = FutureProvider(
  (ref) => ref.watch(waitlistRepositoryProvider).list(),
);
