"""Apply one explicitly selected SQL migration in a transaction."""
import argparse
import sys
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("migration", help="Filename within database/migrations")
    args = parser.parse_args()
    directory = ROOT / "database/migrations"
    path = (directory / args.migration).resolve()
    if path.parent != directory.resolve() or path.suffix != ".sql":
        parser.error("Select a SQL file directly within database/migrations")
    with psycopg2.connect(dbname=settings.POSTGRES_DB, user=settings.POSTGRES_USER,
                         password=settings.POSTGRES_PASSWORD, host=settings.POSTGRES_HOST,
                         port=settings.POSTGRES_PORT) as connection:
        with connection.cursor() as cursor:
            cursor.execute(path.read_text(encoding="utf-8"))
    print(f"Applied {path.name}")


if __name__ == "__main__":
    main()
