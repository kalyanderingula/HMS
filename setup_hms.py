"""Install, initialize, and run HMS from one command.

Usage:
    python setup_hms.py
    python setup_hms.py --setup-only
    python setup_hms.py --skip-bootstrap
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements-runtime.txt"
INSTALL_MARKER = VENV / ".hms-requirements.sha256"
POSTGRES_CONTAINER = "hms_postgres"


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    print(f"\n> {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=ROOT, check=check, env=env)


def output(command: list[str]) -> str:
    result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    return result.stdout.strip()


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_command(name: str, installation_hint: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"'{name}' was not found. {installation_hint}")


def ensure_virtual_environment(skip_install: bool) -> Path:
    python = venv_python()
    if not python.exists():
        print("Creating Python virtual environment...", flush=True)
        run([sys.executable, "-m", "venv", str(VENV)])

    if skip_install:
        return python

    requirements_hash = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    installed_hash = INSTALL_MARKER.read_text(encoding="utf-8").strip() if INSTALL_MARKER.exists() else ""
    if requirements_hash != installed_hash:
        print("Installing HMS runtime dependencies...", flush=True)
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        INSTALL_MARKER.write_text(requirements_hash, encoding="utf-8")
    else:
        print("Python dependencies are already up to date.", flush=True)
    return python


def start_postgres(reset_database: bool, confirmed: bool) -> None:
    ensure_command("docker", "Install and start Docker Desktop, then run this command again.")
    if output(["docker", "info", "--format", "{{.ServerVersion}}"]):
        pass
    else:
        raise RuntimeError("Docker Desktop is installed but its engine is not running.")

    if reset_database:
        if not confirmed:
            raise RuntimeError("Database reset deletes all local HMS data. Repeat with --reset-database --yes to confirm.")
        run(["docker", "compose", "down", "-v"])

    run(["docker", "compose", "up", "-d", "postgres"])
    print("Waiting for PostgreSQL health check", end="", flush=True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status = output(["docker", "inspect", "--format", "{{.State.Health.Status}}", POSTGRES_CONTAINER])
        if status == "healthy":
            print(" ready.", flush=True)
            return
        if status == "unhealthy":
            print(flush=True)
            run(["docker", "compose", "logs", "postgres"], check=False)
            raise RuntimeError("PostgreSQL became unhealthy. Review the log above.")
        print(".", end="", flush=True)
        time.sleep(2)
    print(flush=True)
    run(["docker", "compose", "logs", "postgres"], check=False)
    raise RuntimeError("PostgreSQL did not become healthy within 180 seconds.")


def bootstrap(python: Path) -> None:
    run([str(python), str(ROOT / "scripts" / "bootstrap.py")], env=os.environ.copy())


def serve(python: Path, port: int, reload_enabled: bool) -> None:
    command = [str(python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)]
    if reload_enabled:
        command.append("--reload")
    print(f"\nHMS is ready. Open http://localhost:{port}/", flush=True)
    print("Press Ctrl+C to stop the API. PostgreSQL data will remain available.", flush=True)
    run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up PostgreSQL, initialize HMS, and start the application.")
    parser.add_argument("--port", type=int, default=8000, help="FastAPI port (default: 8000)")
    parser.add_argument("--setup-only", action="store_true", help="Prepare everything but do not start FastAPI")
    parser.add_argument("--skip-bootstrap", action="store_true", help="Skip migrations, demo seeds, and DB validation")
    parser.add_argument("--skip-install", action="store_true", help="Skip Python dependency installation")
    parser.add_argument("--no-reload", action="store_true", help="Run Uvicorn without auto-reload")
    parser.add_argument("--reset-database", action="store_true", help="Delete and recreate the local PostgreSQL volume")
    parser.add_argument("--yes", action="store_true", help="Confirm the destructive --reset-database operation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        os.chdir(ROOT)
        python = ensure_virtual_environment(args.skip_install)
        start_postgres(args.reset_database, args.yes)
        if not args.skip_bootstrap:
            bootstrap(python)
        if not args.setup_only:
            serve(python, args.port, not args.no_reload)
        else:
            print("\nHMS setup completed successfully. Start later with .\\run.ps1", flush=True)
        return 0
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
        return 130
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nSETUP FAILED: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
