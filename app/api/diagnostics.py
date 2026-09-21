from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.config import get_db
from scripts.diagnostic_catalog import DIAGNOSTIC_CATALOG


router = APIRouter(
    prefix="/diagnostics",
    tags=["Diagnostic Catalog"],
    dependencies=[Depends(require_roles([
        "doctor", "telemedicine_doctor", "nurse", "lab_technician", "pathologist",
        "radiologist", "receptionist", "admin", "super_admin",
    ]))],
)


@router.get("/categories")
async def diagnostic_categories():
    """Return the category hierarchy and the expected report authorizer."""
    hierarchy = {}
    for item in DIAGNOSTIC_CATALOG:
        category = hierarchy.setdefault(item["category"], {})
        subcategory = category.setdefault(item["subcategory"], {
            "test_count": 0, "approving_specialties": set()
        })
        subcategory["test_count"] += 1
        subcategory["approving_specialties"].add(item["approving_specialty"])
    return [{
        "category": category,
        "subcategories": [{
            "subcategory": name, "test_count": details["test_count"],
            "approving_specialties": sorted(details["approving_specialties"]),
        } for name, details in sorted(subcategories.items())],
    } for category, subcategories in sorted(hierarchy.items())]


@router.get("/catalog")
async def diagnostic_catalog(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    approver: Optional[str] = None,
    q: Optional[str] = Query(default=None, min_length=1, max_length=100),
):
    """Search tests, parameters, specimens and approval specialties."""
    rows = DIAGNOSTIC_CATALOG
    if category:
        rows = [r for r in rows if r["category"].casefold() == category.casefold()]
    if subcategory:
        rows = [r for r in rows if r["subcategory"].casefold() == subcategory.casefold()]
    if approver:
        rows = [r for r in rows if approver.casefold() in r["approving_specialty"].casefold()]
    if q:
        needle = q.casefold()
        rows = [r for r in rows if needle in " ".join([
            r["code"], r["category"], r["subcategory"], r["name"],
            r["approving_specialty"], *r["parameters"], r["specimen"] or "",
        ]).casefold()]
    return {"count": len(rows), "tests": rows}


@router.get("/approval-routing")
async def diagnostic_approval_routing(q: Optional[str] = None):
    """Expose the report type -> qualified approving-specialty mapping."""
    rows = DIAGNOSTIC_CATALOG
    if q:
        needle = q.casefold()
        rows = [r for r in rows if needle in f'{r["name"]} {r["code"]}'.casefold()]
    return [{
        "test_code": r["code"], "test_name": r["name"],
        "category": r["category"],
        "approving_specialty": r["approving_specialty"],
        "workflow": "Technician acquisition/entry -> qualified doctor authorization -> final report",
    } for r in rows]


@router.get("/critical-results")
async def critical_results_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Critical diagnostic results with release, notification, and acknowledgement state."""
    rows = (await db.execute(text("""
        SELECT 'Laboratory' source_module, e.result_entry_id::text source_id,
               o.order_number, p.mrn, concat_ws(' ',p.first_name,p.last_name) patient_name,
               t.test_name, e.approved_at released_at, e.acknowledged_at,
               n.status notification_status, n.sent_at notification_sent_at
        FROM laboratory.lab_result_entries e
        JOIN laboratory.lab_order_items i USING(order_item_id)
        JOIN laboratory.lab_orders o USING(lab_order_id)
        JOIN laboratory.lab_tests t USING(test_id)
        JOIN patient.patients p USING(patient_id)
        JOIN laboratory.lab_result_parameters rp USING(result_entry_id)
        LEFT JOIN LATERAL (
            SELECT status,sent_at FROM core.notifications
            WHERE source_module='Laboratory' AND source_reference_id=e.result_entry_id
            ORDER BY created_at DESC LIMIT 1
        ) n ON true
        WHERE rp.result_flag='Critical'
        GROUP BY e.result_entry_id,o.order_number,p.mrn,p.first_name,p.last_name,t.test_name,
                 e.approved_at,e.acknowledged_at,n.status,n.sent_at
        UNION ALL
        SELECT 'Radiology',r.report_id::text,o.order_number,p.mrn,
               concat_ws(' ',p.first_name,p.last_name),t.test_name,r.reported_at,
               r.acknowledged_at,n.status,n.sent_at
        FROM radiology.radiology_reports r
        JOIN radiology.imaging_studies s USING(study_id)
        JOIN radiology.radiology_appointments a USING(radiology_appointment_id)
        JOIN radiology.radiology_order_items i USING(order_item_id)
        JOIN radiology.radiology_orders o USING(radiology_order_id)
        JOIN radiology.radiology_tests t USING(radiology_test_id)
        JOIN patient.patients p ON p.patient_id=o.patient_id
        LEFT JOIN LATERAL (
            SELECT status,sent_at FROM core.notifications
            WHERE source_module='Radiology' AND source_reference_id=r.report_id
            ORDER BY created_at DESC LIMIT 1
        ) n ON true
        WHERE r.is_critical IS TRUE
        ORDER BY released_at DESC NULLS LAST
    """))).mappings().all()
    return [dict(row) for row in rows]
