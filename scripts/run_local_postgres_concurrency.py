"""Run PostgreSQL-only tests in a generated disposable local schema."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings

def main():
    base = get_settings().database_url
    host = urlsplit(base.replace('postgresql+psycopg://', 'postgresql://')).hostname
    if host not in {'127.0.0.1', 'localhost'}:
        raise SystemExit('Safety stop: concurrency helper accepts only local PostgreSQL.')
    schema = 'slotbridge_concurrency_' + uuid4().hex
    if not schema.startswith('slotbridge_concurrency_'):
        raise SystemExit('Unsafe temporary schema name.')
    admin = create_engine(base)
    with admin.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}')); connection.commit()
    test_url = make_url(base).update_query_dict({'options': f'-csearch_path={schema},public'}).render_as_string(hide_password=False)
    env = {**os.environ, 'DATABASE_URL': test_url, 'SLOTBRIDGE_ENVIRONMENT': 'test'}
    try:
        from app.models import Base
        test_engine = create_engine(test_url)
        Base.metadata.create_all(test_engine); test_engine.dispose()
        subprocess.run([os.fspath(os.path.join('.venv','Scripts','python.exe')), '-m', 'pytest', 'tests/test_booking_concurrency.py', '-q'], check=True, env=env)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE')); connection.commit()
        admin.dispose()

if __name__ == '__main__': main()
