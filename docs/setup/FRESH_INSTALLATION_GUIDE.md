# HMS Fresh Installation and Startup Guide

This guide explains how to install the HMS project on a new Windows computer, create its PostgreSQL database with Docker, connect through pgAdmin, seed the required data, and start the application.

## 1. Software to install

Install these tools before opening the project:

1. **Git** — to clone the repository.
2. **Python 3.10 or newer** — enable **Add Python to PATH** during installation.
3. **Docker Desktop** — use the WSL 2 backend and make sure Docker Desktop is running.
4. **pgAdmin 4** — optional; the application works without it, but it is useful for viewing the database.
5. **VS Code** — optional editor.

Verify the required commands in PowerShell:

```powershell
git --version
python --version
docker --version
docker compose version
```

## 2. Open the correct project directory

Clone or copy the repository, then open the **inner HMS directory that contains `main.py` and `docker-compose.yml`**:

```powershell
cd "C:\path\to\HMS"
Get-ChildItem main.py, docker-compose.yml, requirements-runtime.txt
```

All commands in this guide must be run from this directory.

## One-command installation and startup

After installing Python and Docker Desktop, the entire normal setup can be run with:

```powershell
python setup_hms.py
```

This creates `.venv`, installs runtime dependencies, starts and waits for PostgreSQL, runs migrations and seed scripts, validates the database, and starts HMS at `http://localhost:8000/`.

Useful options:

```powershell
python setup_hms.py --setup-only       # Install and initialize without starting the API
python setup_hms.py --skip-bootstrap   # Daily start without rerunning migrations/seeds
python setup_hms.py --port 8001        # Use a different web port
python setup_hms.py --no-reload        # Disable development auto-reload
```

The protected reset command permanently deletes all local database data:

```powershell
python setup_hms.py --reset-database --yes
```

The remaining sections document each step separately for troubleshooting and manual administration.

## 3. Create the Python environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-runtime.txt
```

Use `requirements-runtime.txt` for running HMS. The larger `requirements.txt` also installs optional AI, reporting, and infrastructure packages.

## 4. Environment configuration

For local development, the defaults in `app/config.py` match `docker-compose.yml`, so `.env` is optional.

If database credentials or ports are changed, create `.env` beside `main.py` and make its values match the PostgreSQL service in `docker-compose.yml`:

```env
POSTGRES_DB=hospital_management_system
POSTGRES_USER=hms_admin
POSTGRES_PASSWORD=<same password configured in docker-compose.yml>
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
JWT_SECRET=<generate-a-long-random-secret>
AUTH_COOKIE_SECURE=false
```

Never commit production passwords or JWT secrets. Set `AUTH_COOKIE_SECURE=true` when serving over HTTPS.

## 5. Start PostgreSQL first

```powershell
docker compose up -d postgres
docker compose ps
```

Wait until `hms_postgres` reports `healthy`. Follow initialization when needed:

```powershell
docker compose logs -f postgres
```

Press `Ctrl+C` to stop following the log; PostgreSQL remains running.

On the first start of an empty Docker volume, Docker automatically runs `scripts/init-db.sh`. It executes `database/schemas/` in dependency order and then applies `database/migrations/*.sql`. Do not manually run individual schema files during a normal installation.

## 6. Create master data and demo accounts

After PostgreSQL is healthy, run:

```powershell
python scripts/bootstrap.py
```

This is the first Python setup file to run. It executes:

1. `scripts/migrate_all.py` — applies pending migrations safely.
2. `scripts/seed_all.py` — creates master data and demo employee, doctor, receptionist, patient, and operational accounts in dependency order.
3. `scripts/check_database.py` — verifies database connectivity and ORM compatibility.

Choose seed passwords before bootstrap in a shared environment:

```powershell
$env:HMS_INITIAL_ADMIN_PASSWORD = "Choose-A-Strong-Admin-Password"
$env:HMS_DEMO_PASSWORD = "Choose-A-Demo-Password"
python scripts/bootstrap.py
```

These variables apply to the current PowerShell session. Users should change temporary passwords at first login.

## 7. Start HMS

```powershell
.\run.ps1
```

Or start it manually:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Login: `http://localhost:8000/`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Admin Portal after login: `http://localhost:8000/admin`

Keep this terminal open. Stop the API with `Ctrl+C`.

## 8. Connect pgAdmin

In pgAdmin, right-click **Servers** and select **Register > Server**.

General tab:

- Name: `HMS Local`

Connection tab:

- Host name/address: `localhost`
- Port: `5434`
- Maintenance database: `hospital_management_system`
- Username: `hms_admin`
- Password: the `POSTGRES_PASSWORD` configured in `docker-compose.yml`
- Save password: optional locally

Browse `Servers > HMS Local > Databases > hospital_management_system > Schemas` after saving. If pgAdmin runs in another Docker container, use `host.docker.internal` instead of `localhost`.

## Required execution order

| Order | File or command | Purpose |
|---:|---|---|
| 1 | `docker compose up -d postgres` | Starts PostgreSQL; `scripts/init-db.sh` automatically creates schemas on a new volume |
| 2 | `python scripts/bootstrap.py` | Applies migrations, runs all seed scripts, and validates the database |
| 3 | `.\run.ps1` | Starts FastAPI and serves the frontend |
| 4 | `http://localhost:8000/` | Opens the HMS login page |

Do not start with `seed_admin.py`, `seed_receptionist.py`, or an individual SQL file. `scripts/bootstrap.py` controls the dependency order.

## Normal daily startup

After initial installation:

```powershell
docker compose up -d postgres
.\run.ps1
```

Stop the API with `Ctrl+C`, then stop PostgreSQL without deleting its data:

```powershell
docker compose down
```

## Updating an existing installation

```powershell
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-runtime.txt
docker compose up -d postgres
python scripts/bootstrap.py
.\run.ps1
```

Bootstrap is rerunnable: migrations are tracked and seed scripts update or reuse their records.

## Resetting the database

The following permanently deletes the local HMS PostgreSQL volume and all its hospital data:

```powershell
docker compose down -v
docker compose up -d postgres
python scripts/bootstrap.py
```

Only use this for an intentional full local reset. Normal `docker compose down` preserves data.

## Troubleshooting

### PostgreSQL is not healthy

```powershell
docker compose ps
docker compose logs postgres
netstat -ano | findstr :5434
```

Confirm Docker Desktop is running and port `5434` is free.

### Python cannot import a package

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-runtime.txt
```

### Database password authentication fails

The values in `.env`, `app/config.py`, and `docker-compose.yml` must agree. Changing the Compose password does not change the password already stored in an existing PostgreSQL volume.

### Database tables are missing

```powershell
docker compose logs postgres
python scripts/migrate_all.py
python scripts/check_database.py
```

Schema initialization runs automatically only for a new empty volume. Do not delete a volume unless losing its data is acceptable.

### Port 8000 is already used

```powershell
.\run.ps1 -Port 8001
```

Then open `http://localhost:8001/`.
