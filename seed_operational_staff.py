"""Create idempotent demo accounts for operational staff portals.

Override the temporary password with HMS_DEMO_PASSWORD before running outside a
local demonstration environment. Every seeded user must change it at first login.
"""
import asyncio
import os
from datetime import date

from sqlalchemy import select

from app.api.auth import Role, User, UserRole, hash_password
from app.config import async_session, engine
from app.models.department import Department, SubDepartment  # register FK tables
from app.models.employee import Employee
from app.models.patient import Patient  # noqa: F401 - registers User.patient_id FK target


TEMPORARY_PASSWORD = os.getenv("HMS_DEMO_PASSWORD", "HmsDemo@2026")
STAFF = (
    ("SURG-001", "Vikram", "Sen", "surgeon", "surgeon.demo@hms.local"),
    ("OTN-001", "Maya", "Das", "ot_nurse", "ot.nurse@hms.local"),
    ("ANES-001", "Rohan", "Iyer", "anesthesiologist", "anesthesia.demo@hms.local"),
    ("ER-001", "Asha", "Rao", "emergency_staff", "emergency.staff@hms.local"),
    ("PHARM-001", "Priya", "Sharma", "pharmacist", "pharmacist.demo@hms.local"),
    ("LAB-001", "Lakshmi", "Nair", "lab_technician", "lab.demo@hms.local"),
    ("NURSE-001", "Neha", "Patel", "nurse", "nurse.demo@hms.local"),
    ("ACCT-001", "Arjun", "Mehta", "accountant", "accounts.demo@hms.local"),
    ("RAD-001", "Riya", "Kapoor", "radiologist", "radiology.demo@hms.local"),
    ("BLOOD-001", "Anil", "Kumar", "blood_bank_technician", "bloodbank.demo@hms.local"),
)


async def seed_operational_staff() -> None:
    async with async_session() as db:
        for employee_number, first_name, last_name, role_name, email in STAFF:
            role = await db.scalar(select(Role).where(Role.role_name == role_name))
            if not role:
                role = Role(role_name=role_name)
                db.add(role)
                await db.flush()

            employee = await db.scalar(
                select(Employee).where(Employee.employee_number == employee_number)
            )
            if not employee:
                employee = Employee(
                    employee_number=employee_number,
                    first_name=first_name,
                    last_name=last_name,
                    gender="Other",
                    date_of_birth=date(1990, 1, 1),
                    date_of_joining=date.today(),
                    employment_status="active",
                    official_email=email,
                )
                db.add(employee)
                await db.flush()

            user = await db.scalar(select(User).where(User.username == employee_number))
            if not user:
                user = User(
                    username=employee_number,
                    email=email,
                    password_hash=hash_password(TEMPORARY_PASSWORD),
                    status="active",
                    must_change_password=True,
                    employee_id=employee.employee_id,
                )
                db.add(user)
                await db.flush()

            assignment = await db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.user_id,
                    UserRole.role_id == role.role_id,
                )
            )
            if not assignment:
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

        await db.commit()

    print("Operational staff accounts are ready:")
    for employee_number, _, _, role_name, _ in STAFF:
        print(f"  {employee_number:<12} {role_name}")
    print("Temporary password: value of HMS_DEMO_PASSWORD (default: HmsDemo@2026)")
    print("All newly created accounts must change their password after login.")


if __name__ == "__main__":
    async def main() -> None:
        try:
            await seed_operational_staff()
        finally:
            await engine.dispose()

    asyncio.run(main())
