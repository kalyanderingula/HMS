import pytest
import uuid
from fastapi import HTTPException

from app.api.diagnostics import (
    diagnostic_approval_routing,
    diagnostic_catalog,
    diagnostic_categories,
)
from app.api.auth import CurrentUser
from app.api.laboratory import approve_lab_results, calculated_result_flag
from app.api.radiology import submit_radiology_report
from app.schemas.radiology import RadiologyReportCreateRequest
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_diagnostic_catalog_contains_major_clinical_areas():
    payload = await diagnostic_catalog(category=None, subcategory=None, approver=None, q=None)
    assert payload["count"] >= 70
    categories = {row["category"] for row in payload["tests"]}
    assert {"Laboratory", "Radiology", "Cardiology", "Neurology", "Gastroenterology", "Nuclear Medicine"} <= categories


@pytest.mark.asyncio
async def test_catalog_search_exposes_parameters_and_approver():
    test = (await diagnostic_catalog(q="Chest X-Ray"))["tests"][0]
    assert test["approving_specialty"] == "Radiologist"
    assert "Heart size" in test["parameters"]
    assert test["report_type"] == "Findings and impression"


@pytest.mark.asyncio
async def test_approval_routing_identifies_pathologist():
    route = (await diagnostic_approval_routing(q="CBC"))[0]
    assert "Pathology" in route["approving_specialty"]
    assert "qualified doctor authorization" in route["workflow"]


@pytest.mark.asyncio
async def test_category_hierarchy_is_grouped():
    laboratory = next(row for row in await diagnostic_categories() if row["category"] == "Laboratory")
    names = {row["subcategory"] for row in laboratory["subcategories"]}
    assert {"Hematology", "Clinical Biochemistry", "Microbiology"} <= names


def test_server_calculates_lab_flags_from_reference_limits():
    reference = SimpleNamespace(critical_low=5, critical_high=20, min_value=10, max_value=15)
    assert calculated_result_flag(4, reference) == "Critical"
    assert calculated_result_flag(9, reference) == "Low"
    assert calculated_result_flag(12, reference) == "Normal"
    assert calculated_result_flag(16, reference) == "High"
    assert calculated_result_flag(21, reference) == "Critical"


@pytest.mark.asyncio
async def test_general_doctor_cannot_approve_laboratory_report():
    doctor = CurrentUser(user_id=uuid.uuid4(), username="doctor", roles=["doctor"])
    with pytest.raises(HTTPException) as error:
        await approve_lab_results(uuid.uuid4(), db=None, cu=doctor)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_general_doctor_cannot_sign_radiology_report():
    doctor = CurrentUser(user_id=uuid.uuid4(), username="doctor", roles=["doctor"])
    request = RadiologyReportCreateRequest(
        study_id=uuid.uuid4(), findings="Finding", impression="Impression")
    with pytest.raises(HTTPException) as error:
        await submit_radiology_report(request, db=None, cu=doctor)
    assert error.value.status_code == 403
