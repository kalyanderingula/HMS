"""Seed Receptionist sub-departments, employee profile and login account"""
import asyncio
import os
import secrets
from datetime import date
import bcrypt
from sqlalchemy import select
from app.config import async_session, engine
from app.models.department import Department, SubDepartment
from app.models.employee import Employee, EmployeeCategory, EmployeeType
from app.api.auth import User, Role, UserRole
from app.models.patient import Patient  # noqa: F401 - registers User.patient_id FK target

async def seed_reception():
    async with async_session() as db:
        print("1. Seeding Sub-Departments for Patient Management (Reception)...")
        # Patient Management
        res_pat = await db.execute(select(Department).where(Department.department_code == "DEP-PAT"))
        dept_pat = res_pat.scalars().first()
        if dept_pat:
            subdepts = [
                ("PAT-REC", "Front Desk & Reception", "Main reception and patient welcoming counter"),
                ("PAT-REG", "Patient Registration Counter", "New and returning patient intake and MRN assignment"),
                ("PAT-OPD", "OPD Helpdesk & Scheduling", "Outpatient consultation booking and queue management"),
                ("PAT-ENQ", "Enquiry & Information Desk", "General hospital navigation and information"),
                ("PAT-ADM", "Inpatient Admission Desk", "Bed allotment and admission coordination"),
            ]
            for code, name, desc in subdepts:
                res_s = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_code == code))
                if not res_s.scalars().first():
                    db.add(SubDepartment(
                        department_id=dept_pat.department_id,
                        sub_department_code=code,
                        sub_department_name=name,
                        description=desc
                    ))
            await db.commit()
            print("  -> Added sub-departments for DEP-PAT")

        # Appointment Management
        res_apt = await db.execute(select(Department).where(Department.department_code == "DEP-APT"))
        dept_apt = res_apt.scalars().first()
        if dept_apt:
            for code, name in [("APT-BOOK", "Central Appointment Booking"), ("APT-TELE", "Tele-consultation Scheduling")]:
                res_s = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_code == code))
                if not res_s.scalars().first():
                    db.add(SubDepartment(department_id=dept_apt.department_id, sub_department_code=code, sub_department_name=name))
            await db.commit()

        # Billing Management
        res_bil = await db.execute(select(Department).where(Department.department_code == "DEP-BIL"))
        dept_bil = res_bil.scalars().first()
        if dept_bil:
            for code, name in [("BIL-OPD", "OPD Billing Counter"), ("BIL-IPD", "IPD / Discharge Billing Counter"), ("BIL-INS", "Insurance & TPA Desk")]:
                res_s = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_code == code))
                if not res_s.scalars().first():
                    db.add(SubDepartment(department_id=dept_bil.department_id, sub_department_code=code, sub_department_name=name))
            await db.commit()

        print("2. Seeding Employee Category & Type...")
        res_cat = await db.execute(select(EmployeeCategory).where(EmployeeCategory.category_code == "ADMINISTRATIVE"))
        cat = res_cat.scalars().first()
        if not cat:
            cat = EmployeeCategory(category_code="ADMINISTRATIVE", category_name="Administrative Staff", description="Front desk, HR, Billing, Management")
            db.add(cat)
            await db.flush()

        res_type = await db.execute(select(EmployeeType).where(EmployeeType.type_code == "FULL_TIME"))
        emp_type = res_type.scalars().first()
        if not emp_type:
            emp_type = EmployeeType(type_code="FULL_TIME", type_name="Full Time Permanent", employment_nature="Permanent")
            db.add(emp_type)
            await db.flush()

        print("3. Seeding Receptionist Employee...")
        res_sub = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_code == "PAT-REC"))
        sub_rec = res_sub.scalars().first()

        res_emp = await db.execute(select(Employee).where(Employee.employee_number == "EMP-REC-00001"))
        emp = res_emp.scalars().first()
        if not emp:
            emp = Employee(
                employee_number="EMP-REC-00001",
                employee_category_id=cat.employee_category_id,
                employee_type_id=emp_type.employee_type_id,
                first_name="Sarah",
                last_name="Jenkins",
                gender="Female",
                date_of_birth=date(1995, 4, 12),
                date_of_joining=date(2023, 1, 15),
                employment_status="active",
                official_email="reception@hospital.com",
                official_phone="+1-555-0199",
                department_id=dept_pat.department_id if dept_pat else None,
                sub_department_id=sub_rec.sub_department_id if sub_rec else None
            )
            db.add(emp)
            await db.flush()

        print("4. Seeding Receptionist User Login Account...")
        res_user = await db.execute(select(User).where(User.username == "EMP-REC-00001"))
        user = res_user.scalars().first()
        if not user:
            temporary_password = os.getenv("HMS_DEMO_RECEPTIONIST_PASSWORD") or secrets.token_urlsafe(14)
            pwd_hash = bcrypt.hashpw(temporary_password.encode(), bcrypt.gensalt()).decode()
            user = User(
                username="EMP-REC-00001",
                email="reception@hospital.com",
                password_hash=pwd_hash,
                status="active",
                must_change_password=True,
                employee_id=emp.employee_id
            )
            db.add(user)
            print(f"  Temporary credential for EMP-REC-00001: {temporary_password}")
            await db.flush()

            res_role = await db.execute(select(Role).where(Role.role_name == "receptionist"))
            role = res_role.scalars().first()
            if role:
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

        await db.commit()
        print("=== Receptionist Setup Complete ===")
        print("  Department:     Patient Management (DEP-PAT)")
        print("  Sub-Department: Front Desk & Reception (PAT-REC)")
        print("  Employee ID:    EMP-REC-00001 (Sarah Jenkins)")
        print("  Username:       EMP-REC-00001")
        print("  Password:       generated only when the account is first created")
        print("  Role:           receptionist")

if __name__ == "__main__":
    async def main():
        try:
            await seed_reception()
        finally:
            await engine.dispose()
    asyncio.run(main())
