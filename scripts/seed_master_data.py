"""Restore idempotent core department and sub-department reference data."""
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings


def main() -> None:
    schema_sql = (ROOT / "database/schemas/02_APPLICATION_SCHEMA_EXTENSIONS.sql").read_text(encoding="utf-8")
    start = schema_sql.index("INSERT INTO core.departments")
    end = schema_sql.index("-- END OF MIGRATION", start)
    seed_sql = schema_sql[start:end]
    with psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
    ) as db:
        with db.cursor() as cursor:
            cursor.execute(seed_sql)
            cursor.execute("SELECT count(*) FROM core.departments")
            department_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM core.sub_departments")
            sub_department_count = cursor.fetchone()[0]
    print(f"Master data ready: {department_count} departments, {sub_department_count} sub-departments")


if __name__ == "__main__":
    main()
