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
            cursor.execute("""INSERT INTO human_resources.shift_schedules
                (shift_code,shift_name,shift_start_time,shift_end_time,is_night_shift)
                VALUES ('DAY','Day Shift','09:00','17:00',false),
                       ('EVENING','Evening Shift','14:00','22:00',false),
                       ('NIGHT','Night Shift','22:00','06:00',true)
                ON CONFLICT(shift_code) DO NOTHING""")
            permissions = (
                ('patient.read','View patient records','patient'),
                ('appointment.manage','Manage appointments','appointment'),
                ('emr.read','View clinical records','emr'),
                ('emr.write','Update clinical records','emr'),
                ('billing.manage','Manage billing','billing'),
                ('roles.manage','Manage employee roles','security'),
            )
            cursor.executemany("""INSERT INTO security.permissions
                (permission_code,permission_name,module)
                VALUES (%s,%s,%s) ON CONFLICT(permission_code) DO NOTHING""", permissions)
            cursor.execute("SELECT count(*) FROM core.departments")
            department_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM core.sub_departments")
            sub_department_count = cursor.fetchone()[0]
    print(f"Master data ready: {department_count} departments, {sub_department_count} sub-departments")


if __name__ == "__main__":
    main()
