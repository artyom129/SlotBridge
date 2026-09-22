# Настройка и запуск SlotBridge

## Требования

- Python 3.12;
- PostgreSQL 17;
- Flutter stable и Android SDK для mobile;
- Docker Desktop только для Docker mode.

Скопируйте безопасный шаблон перед локальным запуском:

~~~powershell
Copy-Item .env.example .env
~~~

Замените development database password и JWT_SECRET собственными локальными
значениями. Файл .env игнорируется Git.

## Windows native PostgreSQL mode

Создайте роль и базу один раз через psql от имени администратора PostgreSQL:

~~~sql
CREATE ROLE slotbridge LOGIN PASSWORD '<local-password>';
CREATE DATABASE slotbridge OWNER slotbridge;
~~~

Укажите URL в .env:

~~~text
DATABASE_URL=postgresql+psycopg://slotbridge:<url-encoded-password>@127.0.0.1:5432/slotbridge
~~~

После этого используйте:

~~~powershell
.\start_slotbridge.bat
~~~

Script проверяет Python и PostgreSQL service, создаёт .venv при необходимости,
устанавливает изменившиеся requirements, применяет migrations, запускает
идемпотентный development seed и FastAPI на порту 8000.

Остановка backend:

~~~powershell
.\stop_slotbridge.bat
~~~

Команда не останавливает PostgreSQL Windows service.

## Ручной backend setup

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python scripts\seed_domain.py
python run.py
~~~

Проверка:

- Swagger: <http://127.0.0.1:8000/docs>
- Liveness: <http://127.0.0.1:8000/api/v1/health/live>
- Readiness: <http://127.0.0.1:8000/api/v1/health/ready>

## Docker mode

~~~powershell
Copy-Item .env.example .env
docker compose up --build
docker compose exec slotbridge python scripts/seed_domain.py
~~~

Docker Compose поднимает PostgreSQL и backend. Не запускайте native PostgreSQL
и Docker PostgreSQL одновременно на host port 5432.

Остановка:

~~~powershell
docker compose down
~~~

Named PostgreSQL volume сохраняет данные между обычными restart. Не используйте
docker compose down -v, если данные нужно сохранить.

## Migrations

~~~powershell
alembic current
alembic upgrade head
alembic check
~~~

Новые schema changes оформляются отдельной Alembic revision. Production startup
применяет upgrade head автоматически, но не запускает demo seed.

## Flutter development

~~~powershell
cd mobile
flutter pub get
flutter run --dart-define=SLOTBRIDGE_ENVIRONMENT=development --dart-define=SLOTBRIDGE_API_BASE_URL=http://10.0.2.2:8000
~~~

10.0.2.2 — адрес host machine из Android emulator. Для физического устройства
используйте LAN IP компьютера, например http://192.168.x.x:8000.

Production build использует только HTTPS:

~~~powershell
flutter build apk --release --dart-define=SLOTBRIDGE_ENVIRONMENT=production --dart-define=SLOTBRIDGE_API_BASE_URL=https://slotbridge-api.onrender.com
~~~

Альтернативно helper script создаёт APK в игнорируемом artifacts/android:

~~~powershell
.\scripts\build_android_release.ps1
~~~

## Tests

Backend:

~~~powershell
python -m pytest -q
~~~

Targeted AI and Journey tests:

~~~powershell
python -m pytest -q tests\test_ai_assistant.py tests\test_journeys.py
~~~

Flutter:

~~~powershell
cd mobile
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
~~~

Real PostgreSQL concurrency tests находятся в
tests/test_booking_concurrency.py. GitHub Actions запускает их отдельно после
migrations, seed и основной regression suite.

## Production configuration

Production работает на Render с Supabase PostgreSQL. Supabase Auth не
используется.

Минимальные secrets в Render:

- DATABASE_URL — Supabase Session pooler URL с sslmode=require;
- JWT_SECRET — случайное значение минимум 32 символа;
- GEMINI_API_KEY — ключ Gemini.

Остальные настройки перечислены в .env.production.example и render.yaml.
Реальные значения не должны попадать в source, logs или GitHub Release.

Container startup:

1. ожидает доступность PostgreSQL;
2. выполняет alembic upgrade head;
3. запускает Uvicorn на environment PORT.

Production demo seed выполняется только явно:

~~~text
python scripts/seed_production_demo.py
~~~

Для него временно требуются PRODUCTION_DEMO_SEED_ENABLED=true и
DEMO_PASSWORD из secret storage. Обычный restart/redeploy seed не запускает.

## Environment notes

- .env.example предназначен для local development.
- .env.production.example содержит только placeholder production values.
- CORS_ALLOWED_ORIGINS можно оставить пустым для native Flutter app.
- Release Flutter build отклоняет HTTP API URL.
- GEMINI_API_KEY используется только backend.
- Keystore, key.properties, APK, build directories и logs игнорируются Git.
