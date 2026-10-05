import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2
from app.config import settings

conn = psycopg2.connect(
    dbname=settings.POSTGRES_DB,
    user=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    host=settings.POSTGRES_HOST,
    port=settings.POSTGRES_PORT
)
cur = conn.cursor()
cur.execute("""
    SELECT table_schema, table_name 
    FROM information_schema.tables 
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema') AND table_type = 'BASE TABLE'
    ORDER BY table_schema, table_name;
""")
tables = cur.fetchall()
populated = []
total_rows = 0
for s, t in tables:
    try:
        cur.execute(f'SELECT count(*) FROM "{s}"."{t}"')
        cnt = cur.fetchone()[0]
        if cnt > 0:
            populated.append((f"{s}.{t}", cnt))
            total_rows += cnt
    except Exception:
        conn.rollback()

print(f"Total populated tables: {len(populated)}")
print(f"Total records inserted: {total_rows}")
for tbl, cnt in populated:
    print(f"  {tbl}: {cnt}")

