# Архитектура SlotBridge

SlotBridge состоит из Flutter-клиента, FastAPI backend и PostgreSQL. Gemini API
подключён как внешний сервис только через backend.

~~~text
┌──────────────────────┐
│ Flutter Mobile       │
│ Riverpod / GoRouter  │
└──────────┬───────────┘
           │ HTTPS, JSON, JWT
           ▼
┌──────────────────────┐        HTTPS        ┌──────────────────┐
│ FastAPI Backend      │ ──────────────────► │ Gemini API       │
│ RBAC / booking / AI  │ ◄────────────────── │ language intent  │
└──────────┬───────────┘                     └──────────────────┘
           │ SQLAlchemy, transactions
           ▼
┌──────────────────────┐
│ PostgreSQL           │
│ Alembic-managed      │
└──────────────────────┘
~~~

Gemini не соединяется с PostgreSQL и не получает database credentials.

## Mobile

Flutter-приложение отвечает за пользовательский интерфейс, навигацию и
локальное состояние запроса. Riverpod управляет состоянием экранов, GoRouter —
маршрутами, Dio — HTTPS API, secure storage — JWT на устройстве.

Клиент не рассчитывает доступность и не принимает окончательное решение о
booking. Он показывает данные backend и отправляет выбранный пользователем
вариант.

## Backend

FastAPI предоставляет auth, catalog, schedules, availability, appointments,
waitlist, AI и journeys API. SQLAlchemy session привязана к запросу; успешная
операция фиксируется одной транзакцией, исключение приводит к rollback.

RBAC разделяет CLIENT, EMPLOYEE и ADMIN операции. Tenant isolation проверяется
по membership и organization_id. Клиент не может передать собственные
organization_id, client_user_id или рассчитанный ends_at для записи.

## Database

PostgreSQL — источник истины для пользователей, организаций, расписаний,
записей, waitlist и audit history. Схема меняется только через Alembic.
Текущий head: **20260919_0005**.

SQLite остаётся только в изолированной legacy integration demo и не
используется booking engine.

## Booking safety

Обычная запись и Smart Journey используют одинаковые доменные проверки:

1. backend проверяет роль, tenant, branch, employee и service;
2. availability учитывает расписание, перерывы, исключения, блокировки и
   активные записи;
3. Idempotency-Key защищает повтор одного и того же запроса;
4. PostgreSQL advisory locking сериализует конкурирующие команды;
5. exclusion constraint запрещает пересечение BOOKED, CONFIRMED и IN_PROGRESS
   интервалов одного сотрудника;
6. appointment, status history и audit event записываются транзакционно.

Приложение может показать слот, который другой пользователь займёт мгновением
раньше. В этом случае database constraint возвращает conflict, а UI запускает
Conflict Rescue и запрашивает свежую availability.

## Multi-Service Smart Journey

Journey planner принимает упорядоченный список из 2–6 услуг, дату и временное
окно. Для каждого шага он получает реальные интервалы через общий availability
service и строит допустимые последовательности без пересечений.

Из кандидатов выбираются три стратегии:

- FASTEST — минимальная общая длительность и ожидание;
- EARLIEST — самое раннее начало;
- FEWEST_EMPLOYEES — минимальное число специалистов.

Booking всего маршрута выполняется одной транзакцией. При конфликте любого шага
не сохраняется ни одна частичная запись; клиент получает JOURNEY_CONFLICT и
может запросить новый маршрут.

## AI

Flutter отправляет текст и минимальный контекст в FastAPI. Backend передаёт
Gemini только данные, необходимые для текущего запроса. Модель выбирает один из
разрешённых инструментов, но не выполняет database mutation напрямую.

Read-инструменты возвращают catalog и availability. Mutation-инструменты
создают подписанный короткоживущий confirmation token. Booking, reschedule,
cancel или waitlist выполняются только после явного подтверждения клиента и
повторной backend-проверки.

Backend различает timeout, network failure, rate limit, auth failure и invalid
response. Для временных ошибок предусмотрены retry и fallback Gemini model.
Логи содержат только безопасную категорию ошибки и HTTP status, без prompt,
API key или пользовательских данных.

## Infrastructure

- Render запускает Docker-контейнер FastAPI и предоставляет HTTPS.
- Supabase используется только как managed PostgreSQL с обязательным SSL.
- Startup ожидает database, выполняет alembic upgrade head и запускает Uvicorn
  на PORT, переданном Render.
- Demo seed в production запускается только отдельной защищённой командой.
- GitHub Releases хранит Android APK; version endpoint публикует URL, changelog,
  versionCode и SHA-256.

Local Windows mode и Docker Compose используют ту же FastAPI/SQLAlchemy
архитектуру и те же Alembic migrations.
