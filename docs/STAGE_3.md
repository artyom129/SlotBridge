# SlotBridge — Stage 3 implementation report

Date: 2026-09-11
Copyright © 2026 Artyom Koncha. All Rights Reserved.
Scope: scheduling and read-only availability; no Appointment or Booking model

## 1. SUMMARY

Stage 3 добавляет полноценный timezone-aware scheduling domain и отдельный
read-only `AvailabilityService`. Сервис отвечает на вопрос, когда конкретный
активный сотрудник может оказать назначенную ему активную услугу в активном
филиале на заданную локальную дату.

Расчёт учитывает несколько рабочих интервалов, замены расписания и выходные на
конкретную дату, регулярные перерывы, абсолютные блокировки, длительность услуги
или существующий employee-specific override и настраиваемый шаг стартов. Все
операции создания бронирования намеренно отсутствуют. Версия FastAPI-приложения
обновлена до `3.0.0`; legacy integration gateway сохранён.

## 2. MODELS CREATED

Добавлены четыре SQLAlchemy-модели:

- `WorkSchedule`: повторяющийся локальный рабочий интервал; `day_of_week` имеет
  семантику `0 = Monday, ..., 6 = Sunday`; несколько окон в день разрешены.
- `ScheduleBreak`: повторяющийся локальный недоступный интервал; пересекающиеся
  строки разрешены и нормализуются движком.
- `ScheduleException`: либо полный выходной для локальной даты, либо одно из
  специальных рабочих окон, полностью заменяющих recurring schedule.
- `BlockedSlot`: абсолютный недоступный интервал с автором и nullable-причиной;
  хранится как timezone-aware `DateTime`/PostgreSQL `timestamptz`.

Во всех таблицах есть UUID, tenant-derived `organization_id`, employee/branch
composite foreign keys, `is_active`, timestamps, проверки порядка границ и
индексы путей чтения. Для `ScheduleException` check constraint фиксирует ровно
две допустимые формы: day off без времени либо replacement с полной валидной
парой времени.

## 3. MIGRATION

Alembic revision `20260911_0002` следует за `20260910_0001` и:

1. добавляет employee uniqueness `(id, branch_id, organization_id)`, на которую
   ссылаются tenant-safe schedule foreign keys;
2. создаёт `work_schedules`, `schedule_breaks`, `schedule_exceptions` и
   `blocked_slots`;
3. создаёт lookup indexes и exact-window uniqueness;
4. создаёт partial unique index для одного активного day-off на
   employee/branch/date;
5. имеет обратный downgrade в безопасном порядке зависимостей.

PostgreSQL exclusion constraints проанализированы, но не добавлены на Stage 3.
Пересекающиеся work/break/block интервалы являются допустимым входом и
детерминированно объединяются. Запрещать такие строки в БД не даёт пользы
read-only расчёту. Exclusion constraint для конкурентных Appointment относится
к Stage 4 и не должен преждевременно подменяться ограничением BlockedSlot.

Проверено: одна head `20260911_0002`; полный PostgreSQL offline SQL успешно
генерируется, включая `TIMESTAMP WITH TIME ZONE`, checks, composite FKs и partial
index.

## 4. SCHEDULING RULES

- Базовый график берётся по employee + branch + weekday.
- Несколько активных work windows сортируются и объединяются, если пересекаются
  или соприкасаются.
- Наличие активных exceptions на дату полностью заменяет recurring work.
- Любой активный day-off exception делает дату недоступной.
- Management API не позволяет активному day off сосуществовать с активными
  replacement intervals на той же employee/branch/date.
- Регулярные breaks применяются и к обычному графику, и к replacement hours.
- Пересекающиеся/соседние breaks и blocks объединяются до вычитания.
- Exclusions за границами рабочего окна обрезаются; полная блокировка даёт
  пустой результат.
- Старт допустим только тогда, когда вся абсолютная длительность услуги входит
  в один непрерывный свободный интервал.
- Сетка стартов привязана к началу каждого нормализованного рабочего окна.

## 5. TIMEZONE IMPLEMENTATION

Эффективная IANA timezone определяется строго как:

```text
Branch.timezone (если задана) -> Organization.timezone
```

Параметр `date` трактуется как локальная календарная дата филиала. Recurring и
exception times хранятся как local wall-clock `TIME WITHOUT TIME ZONE`.
`BlockedSlot.starts_at/ends_at` являются абсолютными UTC-compatible instants.

Локальные границы преобразуются через стандартный `zoneinfo`, затем вся
interval arithmetic выполняется в UTC. Ответ преобразуется обратно в effective
timezone и содержит offset. Несуществующее локальное время в DST gap даёт
`INVALID_LOCAL_SCHEDULE_TIME`; при неоднозначной границе fold выбирается
детерминированно как `fold=0`. Тесты покрывают `Asia/Almaty`,
`America/New_York`, branch override, organization fallback, invalid zone и
spring-forward с сохранением реальной длительности услуги.

## 6. AVAILABILITY ALGORITHM

`AvailabilityService.calculate(branch_id, employee_id, service_id, local_date)`:

1. загружает branch, organization, employee и service;
2. проверяет active-state, branch membership и tenant consistency;
3. проверяет `EmployeeService` и выбирает duration override либо
   `Service.duration_minutes`;
4. разрешает effective timezone и UTC-границы локального дня;
5. выбирает date exceptions либо recurring work windows;
6. загружает и объединяет recurring breaks;
7. одним запросом загружает все active blocks, пересекающие день;
8. вычитает объединённые exclusions из объединённых work windows;
9. генерирует кандидаты с configured step и оставляет только полностью
   помещающиеся интервалы;
10. возвращает отдельный DTO-result, который API переводит в Pydantic schema.

Appointment и reservation state в алгоритме отсутствуют по границе Stage 3.

## 7. API ENDPOINTS

Read-only, authenticated:

```http
GET /availability?branch_id=<uuid>&employee_id=<uuid>&service_id=<uuid>&date=2026-09-21
```

Response содержит `date`, effective `timezone`,
`service_duration_minutes`, `slot_interval_minutes` и массив `{start, end}`.
ORM-модели наружу не возвращаются. Domain errors имеют стабильные `code` и
читаемый `message`, включая not found, inactive resources, assignment mismatch
и invalid timezone configuration.

ADMIN create/full-update endpoints:

- `POST /admin/work-schedules`
- `PUT /admin/work-schedules/{schedule_id}`
- `POST /admin/schedule-breaks`
- `PUT /admin/schedule-breaks/{break_id}`
- `POST /admin/schedule-exceptions`
- `PUT /admin/schedule-exceptions/{exception_id}`
- `POST /admin/blocked-slots`
- `PUT /admin/blocked-slots/{block_id}`

EMPLOYEE self-service:

- `POST /employee/blocked-slots`
- `PUT /employee/blocked-slots/{block_id}`

Минимальный management API намеренно не раздувается универсальным CRUD,
delete/list abstraction или booking-командами. Деактивация поддерживается
полем `is_active` в full update payload.

## 8. RBAC

- `GET /availability` требует валидный JWT и доступен любой активной
  аутентифицированной роли; все ID всё равно проходят согласованную tenant и
  assignment validation.
- `ADMIN` может создавать и изменять все четыре schedule resource types.
- `EMPLOYEE` не имеет доступа к admin routes и может создавать/изменять только
  `BlockedSlot` собственного `Employee.user_id` в согласованном branch/tenant.
- `CLIENT` не может менять расписание ни через admin, ни через employee routes.
- `organization_id` никогда не принимается из management payload: он выводится
  сервером из проверенной employee/branch scope.

## 9. SEED CHANGES

Идемпотентный development/demo seed теперь устанавливает:

- `SlotBridge Demo` и `Main Branch` с `Asia/Almaty`;
- Alex: Monday-Friday `09:00-18:00`;
- Sam: Monday-Friday `10:00-19:00`;
- Alex: recurring break Monday-Friday `13:00-14:00`;
- Alex: day off `2026-09-21`;
- Sam: training block `2026-09-21 11:00-12:00 Asia/Almaty`, сохраняемый как
  `06:00-07:00 UTC`;
- уже существующие услуги 30/60/90 минут и четыре assignments.

Seed дважды запускается в тесте без дублей: 10 work schedules, 5 breaks,
1 exception и 1 block.

## 10. FILES CREATED

| File | Причина |
|---|---|
| `alembic/versions/20260911_0002_scheduling_availability.py` | Полная schema migration Stage 3 и downgrade |
| `app/api/schedules.py` | Availability route и минимальные RBAC management commands |
| `app/services/__init__.py` | Явный доменный service package |
| `app/services/intervals.py` | Переиспользуемые merge/subtract/slot-generation primitives |
| `app/services/scheduling.py` | Tenant-safe management scope и exception compatibility rules |
| `app/services/availability.py` | Отдельный timezone-aware read-only calculation service |
| `tests/test_intervals.py` | Точные unit tests интервальной арифметики |
| `tests/test_availability.py` | Exact slots, validation, timezone, DST и fixed-query tests |
| `tests/test_schedule_api.py` | ADMIN/EMPLOYEE/CLIENT API и ownership tests |
| `docs/STAGE_3.md` | Этот 16-раздельный implementation/verification report |

## 11. FILES MODIFIED

| File | Причина |
|---|---|
| `.env.example` | Документирован configurable 15-minute slot interval |
| `README.md` | Текущее состояние, правила, API, seed и честные ограничения Stage 3 |
| `app/config.py` | Валидируемая настройка `availability_slot_interval_minutes` (1-60) |
| `app/main.py` | Подключён scheduling router; версия API `3.0.0` |
| `app/models.py` | Новые модели, indexes, checks и tenant composite constraints |
| `app/schemas.py` | Input/output schemas, local-time и aware-datetime validation |
| `scripts/seed_domain.py` | Идемпотентные work/break/exception/block demo rows |
| `tests/conftest.py` | Очистка новых таблиц в PostgreSQL CI в FK-safe порядке |
| `tests/test_domain.py` | Проверка новых seed counts и demo timezone после двойного запуска |

`LICENSE` и `NOTICE` не изменялись. Существующие Stage 1/2 изменения сохранены.

## 12. TEST RESULTS

Локальная финальная проверка:

- полный suite: **50 passed**, 2 external deprecation warnings, 9.70 s;
- исходный Stage 2 + legacy regression subset: **16 passed**, 2 warnings,
  3.93 s;
- interval utilities: **3 passed**;
- availability/timezone/validation/performance: **27 passed**;
- schedule management/RBAC: **4 passed**;
- Python compileall: passed;
- Alembic heads: `20260911_0002 (head)`;
- PostgreSQL offline `alembic upgrade head --sql`: passed;
- `docker compose config --quiet`: passed;
- Docker image build: не выполнен, потому что локальный Docker Desktop engine
  недоступен по `npipe:////./pipe/dockerDesktopLinuxEngine`.

Два warnings приходят из совместимости Starlette TestClient с установленными
httpx/anyio и не являются ошибками SlotBridge. Реальный PostgreSQL container
run/migration drift check должен выполниться существующим CI либо после запуска
Docker Desktop; локально утверждение о нём не подменяется SQLite-результатом.

## 13. PERFORMANCE NOTES

Нет query-per-slot поведения. Независимо от числа кандидатов сервис делает
фиксированный набор lookup-запросов: resources/link, exceptions/work, breaks и
один overlap-query для blocks. Автоматический тест подтверждает ровно 9 SELECT
для результата из 33 слотов.

Lookup indexes соответствуют фильтрам employee/branch/day/date/active и
starts/ends overlap. Нормализация и генерация выполняются в памяти над уже
загруженными интервалами. Redis/cache не добавлялся без измеренной потребности.

## 14. KNOWN ISSUES

- Локально недоступен Docker daemon, поэтому live PostgreSQL upgrade, seed и
  `alembic check` не были повторены вне CI; offline PostgreSQL DDL проверен.
- Текущая Stage 2 identity model не содержит organization membership для CLIENT
  и использует global ADMIN. Availability требует JWT и предотвращает
  смешивание tenant resources, но per-organization catalog visibility потребует
  отдельной membership/policy модели.
- Management API минимален: create, full update и `is_active`; list/delete,
  effective-date ranges и schedule templates отсутствуют.
- Для неоднозначной локальной schedule boundary при осеннем DST используется
  задокументированный `fold=0`; UI для явного выбора fold отсутствует.
- Legacy integration gateway пока использует отдельную SQLite database и не
  является источником availability.

## 15. RISKS

- Availability — моментальный read-only снимок, а не обещание или reservation.
  До Stage 4 два клиента могут увидеть один слот как свободный.
- Без PostgreSQL Appointment exclusion constraint никакой будущий booking route
  нельзя считать защищённым от double booking.
- Изменение timezone после создания absolute blocks меняет их отображаемое
  local time, хотя сам instant остаётся корректным; такая операция должна иметь
  audit/operational policy.
- Сложные исторические timezone изменения зависят от актуальности системной
  IANA/tzdata базы.
- Global ADMIN и широкие authenticated catalog reads следует заменить
  explicit organization memberships до внешнего multi-tenant запуска.

## 16. EXACT RECOMMENDED SCOPE FOR STAGE 4

Stage 4 должен ограничиться атомарным appointment/booking core:

1. Создать tenant-safe `Appointment` с organization, branch, employee, service,
   client, aware UTC start/end, duration/service snapshots, timestamps и
   минимальным status enum (`CONFIRMED`, `CANCELLED`).
2. Добавить append-only appointment status/audit history для create, cancel и
   reschedule с actor/reason.
3. Включить PostgreSQL `btree_gist` и database exclusion constraint по
   employee + `tstzrange(starts_at, ends_at, '[)')` только для активных
   appointment statuses.
4. Реализовать атомарный create command: в одной транзакции повторно проверить
   tenant/service/schedule/break/block availability и вставить Appointment;
   DB conflict вернуть стабильным HTTP 409.
5. Добавить tenant-scoped idempotency key для booking create и безопасный replay
   идентичного результата.
6. Реализовать authenticated create/list/detail/cancel/reschedule endpoints с
   CLIENT ownership, EMPLOYEE assigned-schedule access и ADMIN policy.
7. Для reschedule использовать тот же transaction/exclusion path, не
   delete-then-create без защиты.
8. Начать вычитать активные Appointments в Stage 3 availability service, сохранив
   его read-only характер.
9. Добавить обязательные real-PostgreSQL concurrency tests: два одновременных
   create на один интервал дают ровно один success; также block-vs-book и
   reschedule-vs-book races.
10. Добавить migration upgrade/downgrade, model drift check, deterministic seed
    и exact API/domain tests lifecycle/authorization/idempotency.

Из Stage 4 исключить waitlist, WebSocket/realtime, notifications, provider
writes, payments, AI и Flutter. Они не должны размывать доказательство главного
инварианта: один сотрудник не может иметь два активных appointment на
пересекающееся абсолютное время.
