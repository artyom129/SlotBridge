import '../core/network/api_client.dart';
import '../domain/models.dart';

abstract interface class ReviewRepository {
  Future<Review> create({
    required String appointmentId,
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool isAnonymous = false,
  });
  Future<Review> get(String reviewId);
  Future<Review> forAppointment(String appointmentId);
  Future<Review> update(
    String reviewId, {
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool? isAnonymous,
  });
  Future<ReviewPage> employeeReviews(
    String employeeId, {
    int? rating,
    String sort = 'newest',
  });
  Future<EmployeeRating> employeeRating(String employeeId);
}

class ApiReviewRepository implements ReviewRepository {
  ApiReviewRepository(this._api);
  final ApiClient _api;

  Map<String, dynamic> _payload({
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool? isAnonymous,
  }) => {
    'overall_rating': overallRating,
    'quality_rating': qualityRating,
    'service_rating': serviceRating,
    'punctuality_rating': punctualityRating,
    'comment': comment?.trim().isEmpty == true ? null : comment?.trim(),
    'is_anonymous': ?isAnonymous,
  };

  @override
  Future<Review> create({
    required String appointmentId,
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool isAnonymous = false,
  }) async {
    final response = await _api.post(
      '/reviews',
      data: {
        'appointment_id': appointmentId,
        ..._payload(
          overallRating: overallRating,
          qualityRating: qualityRating,
          serviceRating: serviceRating,
          punctualityRating: punctualityRating,
          comment: comment,
          isAnonymous: isAnonymous,
        ),
      },
    );
    return Review.fromJson(response as JsonMap);
  }

  @override
  Future<Review> get(String reviewId) async =>
      Review.fromJson(await _api.get('/reviews/$reviewId') as JsonMap);

  @override
  Future<Review> forAppointment(String appointmentId) async => Review.fromJson(
    await _api.get('/appointments/$appointmentId/review') as JsonMap,
  );

  @override
  Future<Review> update(
    String reviewId, {
    required int overallRating,
    int? qualityRating,
    int? serviceRating,
    int? punctualityRating,
    String? comment,
    bool? isAnonymous,
  }) async => Review.fromJson(
    await _api.patch(
      '/reviews/$reviewId',
      data: _payload(
        overallRating: overallRating,
        qualityRating: qualityRating,
        serviceRating: serviceRating,
        punctualityRating: punctualityRating,
        comment: comment,
        isAnonymous: isAnonymous,
      ),
    ) as JsonMap,
  );

  @override
  Future<ReviewPage> employeeReviews(
    String employeeId, {
    int? rating,
    String sort = 'newest',
  }) async => ReviewPage.fromJson(
    await _api.get(
      '/employees/$employeeId/reviews',
      queryParameters: {'sort': sort, 'rating': ?rating},
    ) as JsonMap,
  );

  @override
  Future<EmployeeRating> employeeRating(String employeeId) async =>
      EmployeeRating.fromJson(
        await _api.get('/employees/$employeeId/rating') as JsonMap,
      );
}
