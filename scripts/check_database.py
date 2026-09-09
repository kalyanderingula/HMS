"""Read-only database connectivity and model compatibility check."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # Register application models.
from app.config import engine
from app.models.employee import Base
from sqlalchemy import text


async def check():
    async with engine.connect() as conn:
        rows = (await conn.execute(text(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns"
        ))).all()
        columns = {(s, t, c) for s, t, c in rows}
        missing = [f"{t.schema}.{t.name}.{c.name}" for t in Base.metadata.tables.values()
                   for c in t.columns if (t.schema or 'public', t.name, c.name) not in columns]
        print(f"Database connected; checked {len(Base.metadata.tables)} mapped tables.")
        for name in missing:
            print(f"Missing: {name}")
    await engine.dispose()
    return bool(missing)


if __name__ == "__main__":
    sys.exit(asyncio.run(check()))
