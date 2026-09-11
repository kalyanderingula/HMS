"""Apply all pending SQL migrations once, in deterministic filename order."""
import hashlib
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import settings

MIGRATIONS = ROOT / "database" / "migrations"


def connection():
    return psycopg2.connect(dbname=settings.POSTGRES_DB, user=settings.POSTGRES_USER,
                            password=settings.POSTGRES_PASSWORD, host=settings.POSTGRES_HOST,
                            port=settings.POSTGRES_PORT)


def migrate() -> int:
    files = sorted(MIGRATIONS.glob("*.sql"), key=lambda path: path.name)
    with connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('hms_schema_migrations'))")
            cursor.execute("""CREATE TABLE IF NOT EXISTS public.schema_migrations (
                filename text PRIMARY KEY, checksum_sha256 text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            cursor.execute("SELECT filename, checksum_sha256 FROM public.schema_migrations")
            applied = dict(cursor.fetchall())
            count = 0
            for path in files:
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                if path.name in applied:
                    if applied[path.name] != checksum:
                        raise RuntimeError(f"Applied migration was modified: {path.name}")
                    print(f"Already applied: {path.name}")
                    continue
                cursor.execute(sql)
                cursor.execute("INSERT INTO public.schema_migrations(filename, checksum_sha256) VALUES (%s,%s)",
                               (path.name, checksum))
                print(f"Applied: {path.name}")
                count += 1
    print(f"Migration check complete: {count} applied, {len(files) - count} unchanged.")
    return count


if __name__ == "__main__":
    migrate()
