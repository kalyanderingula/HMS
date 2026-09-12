"""Create or refresh a local demonstration patient portal account."""
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.auth import hash_password, verify_password
from app.config import async_session, engine


USERNAME = "PATIENT-001"
PASSWORD = os.getenv("HMS_DEMO_PATIENT_PASSWORD", os.getenv("HMS_DEMO_PASSWORD", "HmsDemo@2026"))


async def seed() -> None:
    async with async_session() as db:
        patient = (await db.execute(text("""
            SELECT p.patient_id, p.mrn, p.first_name, p.last_name
            FROM patient.patients p
            ORDER BY (
                SELECT count(*) FROM appointment.appointments a
                WHERE a.patient_id = p.patient_id
            ) DESC, p.created_at
            LIMIT 1
        """))).mappings().first()
        if not patient:
            raise RuntimeError("No patient record exists. Register a patient first.")

        role_id = await db.scalar(text("""
            INSERT INTO security.roles (role_name)
            VALUES ('patient')
            ON CONFLICT (role_name) DO UPDATE SET role_name = EXCLUDED.role_name
            RETURNING role_id
        """))
        existing = (await db.execute(text("""
            SELECT user_id, patient_id FROM security.users
            WHERE username = :username OR patient_id = :patient_id
            ORDER BY patient_id = :patient_id DESC
            LIMIT 1
        """), {"username": USERNAME, "patient_id": patient["patient_id"]})).mappings().first()

        if existing:
            if existing["patient_id"] not in (None, patient["patient_id"]):
                raise RuntimeError(f"Username {USERNAME} belongs to a different patient")
            user_id = existing["user_id"]
            await db.execute(text("""
                UPDATE security.users
                SET patient_id=:patient_id, password_hash=:password_hash,
                    status='active', must_change_password=false, employee_id=NULL
                WHERE user_id=:user_id
            """), {"patient_id": patient["patient_id"], "password_hash": hash_password(PASSWORD),
                    "user_id": user_id})
        else:
            user_id = await db.scalar(text("""
                INSERT INTO security.users
                    (username, password_hash, status, must_change_password, patient_id)
                VALUES (:username, :password_hash, 'active', false, :patient_id)
                RETURNING user_id
            """), {"username": USERNAME, "password_hash": hash_password(PASSWORD),
                    "patient_id": patient["patient_id"]})

        await db.execute(text("DELETE FROM security.user_roles WHERE user_id=:user_id"), {"user_id": user_id})
        await db.execute(text("""
            INSERT INTO security.identity_links (user_id, identity_type, identity_id)
            VALUES (:user_id, 'patient', :patient_id)
            ON CONFLICT (user_id, identity_type) DO UPDATE SET identity_id=EXCLUDED.identity_id
        """), {"user_id": user_id, "patient_id": patient["patient_id"]})
        await db.execute(text("""
            INSERT INTO security.user_roles (user_id, role_id)
            VALUES (:user_id, :role_id)
        """), {"user_id": user_id, "role_id": role_id})
        stored = (await db.execute(text("""
            SELECT u.password_hash, array_agg(r.role_name ORDER BY r.role_name) roles
            FROM security.users u
            JOIN security.user_roles ur USING (user_id)
            JOIN security.roles r USING (role_id)
            WHERE u.user_id=:user_id AND u.patient_id=:patient_id AND u.status='active'
            GROUP BY u.password_hash
        """), {"user_id": user_id, "patient_id": patient["patient_id"]})).mappings().one()
        if stored["roles"] != ["patient"] or not verify_password(PASSWORD, stored["password_hash"]):
            raise RuntimeError("Patient account verification failed")
        await db.commit()
        print(f"Patient: {patient['first_name']} {patient['last_name']} (MRN {patient['mrn']})")
        print(f"Username: {USERNAME}")
        print(f"Password: {PASSWORD}")
        print("Verified role: patient")


if __name__ == "__main__":
    async def main():
        try:
            await seed()
        finally:
            await engine.dispose()
    asyncio.run(main())
