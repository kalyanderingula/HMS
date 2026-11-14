import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import engine


async def main():
    async with engine.connect() as connection:
        print("DATABASE:", (await connection.execute(text("select current_database(), current_user"))).one())
        migrations = await connection.execute(text("""
            select filename from public.schema_migrations
            where filename >= '009' order by filename
        """))
        print("MIGRATIONS:", [row[0] for row in migrations])
        columns = await connection.execute(text("""
            select table_schema, table_name, column_name
            from information_schema.columns
            where (table_schema='intensive_care_unit' and table_name='icu_admissions'
                   and column_name in ('referring_doctor_id','attending_doctor_id','updated_at','cancellation_reason'))
               or (table_schema='ambulance' and table_name='ambulances'
                   and column_name in ('is_active','updated_at','updated_by'))
               or (table_schema='inventory' and table_name='vendors'
                   and column_name in ('is_active','updated_at','updated_by'))
            order by 1,2,3
        """))
        print("COLUMNS:", [tuple(row) for row in columns])
        roles = await connection.execute(text("""
            select role_name from security.roles
            where role_name in ('icu_staff','ambulance_staff','procurement_staff','procurement_manager')
            order by role_name
        """))
        print("ROLES:", [row[0] for row in roles])
        doctors = await connection.execute(text("""
            select d.doctor_code, concat_ws(' ', e.first_name, e.middle_name, e.last_name)
            from doctor.doctors d join human_resources.employees e using(employee_id)
            order by e.first_name, e.last_name
        """))
        print("DOCTORS:", [tuple(row) for row in doctors])
        doctor_users = await connection.execute(text("""
            select e.employee_number, concat_ws(' ', e.first_name, e.middle_name, e.last_name), r.role_name
            from security.users u
            join human_resources.employees e on e.employee_id=u.employee_id
            join security.user_roles ur on ur.user_id=u.user_id
            join security.roles r on r.role_id=ur.role_id
            where r.role_name in ('doctor','surgeon','telemedicine_doctor')
            order by e.employee_number, r.role_name
        """))
        print("DOCTOR_ROLE_EMPLOYEES:", [tuple(row) for row in doctor_users])
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
