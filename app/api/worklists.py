"""Read APIs for staff queues; all data comes from the existing clinical tables."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import require_roles
from app.config import get_db

router = APIRouter(prefix="/worklists", tags=["Staff Worklists"])


@router.get("/laboratory", dependencies=[Depends(require_roles(["lab_technician", "doctor", "nurse", "admin"]))])
async def laboratory(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""SELECT i.order_item_id, i.test_id, o.order_number, p.mrn,
        concat_ws(' ',p.first_name,p.last_name) AS patient_name, t.test_name, i.order_status,
        o.ordered_at, r.result_entry_id, r.result_status
        FROM laboratory.lab_order_items i JOIN laboratory.lab_orders o USING(lab_order_id)
        JOIN patient.patients p ON p.patient_id=o.patient_id
        JOIN laboratory.lab_tests t USING(test_id)
        LEFT JOIN LATERAL (SELECT result_entry_id,result_status FROM laboratory.lab_result_entries
            WHERE order_item_id=i.order_item_id ORDER BY entered_at DESC LIMIT 1) r ON true
        ORDER BY o.ordered_at DESC LIMIT 200"""))
    return [dict(r) for r in rows.mappings()]


@router.get("/radiology", dependencies=[Depends(require_roles(["radiologist", "doctor", "admin"]))])
async def radiology(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""SELECT i.order_item_id,o.order_number,p.mrn,
        concat_ws(' ',p.first_name,p.last_name) AS patient_name,t.test_name,i.order_status,o.ordered_at
        FROM radiology.radiology_order_items i JOIN radiology.radiology_orders o USING(radiology_order_id)
        JOIN patient.patients p ON p.patient_id=o.patient_id
        JOIN radiology.radiology_tests t USING(radiology_test_id)
        ORDER BY o.ordered_at DESC LIMIT 200"""))
    return [dict(r) for r in rows.mappings()]


@router.get("/prescriptions", dependencies=[Depends(require_roles(["pharmacist", "doctor", "nurse", "admin"]))])
async def prescriptions(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""SELECT pr.prescription_id,pr.prescription_number,p.patient_id,p.mrn,
        concat_ws(' ',p.first_name,p.last_name) AS patient_name, d.generic_name,
        i.drug_id,i.prescription_item_id,i.dosage,i.frequency,i.route,i.duration,
        i.quantity_prescribed,i.quantity_dispensed,
        GREATEST(COALESCE(i.quantity_prescribed,0)-COALESCE(i.quantity_dispensed,0),0) AS quantity_remaining,
        i.item_status,pr.prescription_date,s.status_name
        FROM pharmacy.prescriptions pr JOIN patient.patients p USING(patient_id)
        JOIN pharmacy.prescription_items i USING(prescription_id)
        JOIN pharmacy.drugs d USING(drug_id)
        LEFT JOIN pharmacy.prescription_statuses s USING(prescription_status_id)
        WHERE COALESCE(s.status_name,'Pending') <> 'Cancelled'
        ORDER BY pr.prescription_date DESC LIMIT 200"""))
    return [dict(r) for r in rows.mappings()]
