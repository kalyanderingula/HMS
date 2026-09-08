"""Seed Phase 4 Acute Care (Emergency, Wards/Beds, Surgery, Blood Units)"""
import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.config import async_session
from app.api.auth import Role
from app.models.receptionist_models import Ward, Room, Bed
from app.models.inpatient_emergency_models import (
    EmergencyTriageLevel, BloodGroupType, BloodComponentType, BloodUnit
)

async def seed_phase4():
    async with async_session() as db:
        print("1. Ensuring Phase 4 Roles...")
        for r_name in ["nurse", "surgeon"]:
            res = await db.execute(select(Role).where(Role.role_name == r_name))
            if not res.scalars().first():
                db.add(Role(role_name=r_name))

        print("2. Ensuring Emergency Triage ESI Levels...")
        esi_levels = [
            ("Level 1 - Resuscitation", 1, 0),
            ("Level 2 - Emergent", 2, 10),
            ("Level 3 - Urgent", 3, 30),
            ("Level 4 - Less Urgent", 4, 60),
            ("Level 5 - Non-urgent", 5, 120),
        ]
        for name, rank, resp in esi_levels:
            res = await db.execute(select(EmergencyTriageLevel).where(EmergencyTriageLevel.severity_rank == rank))
            if not res.scalars().first():
                db.add(EmergencyTriageLevel(level_name=name, severity_rank=rank, response_time_minutes=resp))

        print("3. Ensuring Inpatient Wards, Rooms & Available Beds...")
        res_w = await db.execute(select(Ward).where(Ward.ward_code == "WARD-ICU"))
        icu_ward = res_w.scalars().first()
        if not icu_ward:
            icu_ward = Ward(ward_name="Intensive Care Unit (ICU)", ward_code="WARD-ICU", floor_number="3", building_name="Main Wing")
            db.add(icu_ward)
            await db.flush()

            icu_room = Room(ward_id=icu_ward.ward_id, room_number="ICU-BAY-1", floor_number="3")
            db.add(icu_room)
            await db.flush()

            for b_num in ["ICU-B01", "ICU-B02", "ICU-B03"]:
                db.add(Bed(room_id=icu_room.room_id, bed_number=b_num))

        print("4. Ensuring Blood Bank Components and Stock Units...")
        groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        bg_map = {}
        for g in groups:
            res_bg = await db.execute(select(BloodGroupType).where(BloodGroupType.group_name == g))
            bg_obj = res_bg.scalars().first()
            if not bg_obj:
                bg_obj = BloodGroupType(group_name=g)
                db.add(bg_obj)
                await db.flush()
            bg_map[g] = bg_obj.blood_group_type_id

        res_comp = await db.execute(select(BloodComponentType).where(BloodComponentType.component_name == "PRBC"))
        prbc_comp = res_comp.scalars().first()
        if not prbc_comp:
            prbc_comp = BloodComponentType(component_name="PRBC", shelf_life_days=42, storage_temperature="2-6C")
            db.add(prbc_comp)
            await db.flush()

        # Seed sample blood units
        for idx, (grp, b_num) in enumerate([("O+", "BU-OPOS-101"), ("A+", "BU-APOS-102"), ("B+", "BU-BPOS-103")], 1):
            res_u = await db.execute(select(BloodUnit).where(BloodUnit.unit_number == b_num))
            if not res_u.scalars().first():
                db.add(BloodUnit(
                    unit_number=b_num,
                    blood_group_type_id=bg_map.get(grp),
                    blood_component_type_id=prbc_comp.blood_component_type_id,
                    volume_ml=450,
                    collection_date=date.today(),
                    expiry_date=date.today() + timedelta(days=35),
                    status="available"
                ))

        await db.commit()
        print("=== Phase 4 Acute Care Seeding Complete ===")

asyncio.run(seed_phase4())
