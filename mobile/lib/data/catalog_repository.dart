import '../core/errors/app_exception.dart';
import '../core/network/api_client.dart';
import '../domain/models.dart';

abstract interface class CatalogRepository {
  Future<CatalogBootstrap> loadBootstrap();
  Future<List<Employee>> employeesForService(
    Organization organization,
    Branch branch,
    Service service,
  );
}

class ApiCatalogRepository implements CatalogRepository {
  ApiCatalogRepository(this._api);

  final ApiClient _api;

  @override
  Future<CatalogBootstrap> loadBootstrap() async {
    final organizations = ((await _api.get('/organizations')) as List<dynamic>)
        .map((item) => Organization.fromJson(item as JsonMap))
        .where((item) => item.isActive)
        .toList(growable: false);

    for (final organization in organizations) {
      final results = await Future.wait<dynamic>([
        _api.get('/organizations/${organization.id}/branches'),
        _api.get('/organizations/${organization.id}/services'),
      ]);
      final branches = (results[0] as List<dynamic>)
          .map((item) => Branch.fromJson(item as JsonMap))
          .where((item) => item.isActive)
          .toList(growable: false);
      final services = (results[1] as List<dynamic>)
          .map((item) => Service.fromJson(item as JsonMap))
          .where((item) => item.isActive)
          .toList(growable: false);
      if (branches.isNotEmpty && services.isNotEmpty) {
        return CatalogBootstrap(
          organization: organization,
          branch: branches.first,
          services: services,
        );
      }
    }
    throw const AppException(
      'Нет доступного филиала для записи.',
      code: 'no_active_location',
    );
  }

  @override
  Future<List<Employee>> employeesForService(
    Organization organization,
    Branch branch,
    Service service,
  ) async {
    final response = await _api.get(
      '/organizations/${organization.id}/employees',
    );
    final employees = (response as List<dynamic>)
        .map((item) => Employee.fromJson(item as JsonMap))
        .where((item) => item.isActive && item.branchId == branch.id)
        .toList(growable: false);

    final checks = await Future.wait(
      employees.map((employee) async {
        final payload = await _api.get('/employees/${employee.id}/services');
        final offersService = (payload as List<dynamic>)
            .map((item) => Service.fromJson(item as JsonMap))
            .any((item) => item.id == service.id && item.isActive);
        return offersService ? employee : null;
      }),
    );
    return checks.whereType<Employee>().toList(growable: false);
  }
}
