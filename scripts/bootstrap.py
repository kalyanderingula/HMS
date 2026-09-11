"""Prepare an existing HMS database, seed demo data, and validate it."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(relative_path: str) -> None:
    subprocess.run([sys.executable, str(ROOT / relative_path)], cwd=ROOT, check=True)


if __name__ == "__main__":
    run("scripts/migrate_all.py")
    run("scripts/seed_all.py")
    run("scripts/check_database.py")
    print("\nHMS bootstrap completed. Start with: python -m uvicorn main:app --reload")
