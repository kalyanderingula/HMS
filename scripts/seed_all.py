"""Run every HMS demo seed in dependency order from one command."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (
    "scripts/seed_master_data.py",
    "seed_receptionist.py",
    "seed_receptionist_demo.py",
    "seed_phase2_emr.py",
    "seed_phase3_diagnostics.py",
    "seed_phase4_acute_care.py",
    "seed_operational_staff.py",
    "seed_admin.py",
    "scripts/seed_patient_portal.py",
)


def main() -> None:
    environment = os.environ.copy()
    environment.setdefault("HMS_DEMO_PASSWORD", "HmsDemo@2026")
    environment.setdefault("HMS_INITIAL_ADMIN_PASSWORD", "Admin_@_01011990")
    environment.setdefault("HMS_DEMO_RECEPTIONIST_PASSWORD", environment["HMS_DEMO_PASSWORD"])
    environment.setdefault("HMS_DEMO_DOCTOR_PASSWORD", environment["HMS_DEMO_PASSWORD"])
    environment.setdefault("HMS_DEMO_PATIENT_PASSWORD", environment["HMS_DEMO_PASSWORD"])
    for relative_path in SEEDS:
        print(f"\n=== Running {relative_path} ===", flush=True)
        subprocess.run([sys.executable, str(ROOT / relative_path)], cwd=ROOT,
                       env=environment, check=True)
    print("\nAll HMS demo data and accounts are ready.")


if __name__ == "__main__":
    main()
