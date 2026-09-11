"""Integration tests for Milestone 4: Administration, Security & Compliance."""
import uuid
import hashlib
from datetime import date
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from main import app
from app.config import get_db, settings
from app.api.auth import CurrentUser, get_current_user, User, Role, Permission
from app.models.employee import Employee, ShiftSchedule, EmployeeRoster
from app.models.department import Department


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        admin = await session.scalar(select(User).where(User.status == "active"))
        assert admin, "An active seeded user is required"

        async def db_override():
            yield session

        async def user_override():
            return CurrentUser(
                user_id=admin.user_id,
                username=admin.username,
                employee_id=admin.employee_id,
                roles=["super_admin", "admin", "hr_manager"],
                name="System Administrator"
            )

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_current_user] = user_override
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
                yield c, session
        finally:
            app.dependency_overrides.clear()
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_duty_rosters_and_double_booking_prevention(client):
    """Test shift retrieval, roster assignment, and 409 conflict detection for double-booking."""
    c, session = client

    # 1. Get available shifts
    shifts_res = await c.get("/api/v1/rosters/shifts")
    assert shifts_res.status_code == 200
    shifts = shifts_res.json()
    assert len(shifts) >= 1
    shift_id = shifts[0]["shift_schedule_id"]

    # 2. Get an active employee
    emp = await session.scalar(select(Employee).where(Employee.is_active == True))
    if not emp:
        emp = await session.scalar(select(Employee))
    assert emp, "An employee is required for roster testing"
    employee_id = str(emp.employee_id)

    target_date = date(2026, 11, 15).isoformat()

    # 3. Assign duty roster
    roster_payload = {
        "employee_id": employee_id,
        "shift_schedule_id": shift_id,
        "department_id": str(emp.department_id) if emp.department_id else None,
        "roster_date": target_date,
        "notes": "Emergency OPD coverage"
    }
    create_res = await c.post("/api/v1/rosters", json=roster_payload)
    assert create_res.status_code == 201
    roster_data = create_res.json()
    roster_id = roster_data["employee_roster_id"]
    assert roster_data["employee_id"] == employee_id
    assert roster_data["roster_date"] == target_date

    # 4. Attempt double booking on the same date -> expect 409 Conflict
    conflict_res = await c.post("/api/v1/rosters", json=roster_payload)
    assert conflict_res.status_code == 409
    assert "already scheduled" in conflict_res.json()["detail"].lower()

    # 5. List duty rosters for this employee
    list_res = await c.get(f"/api/v1/rosters?employee_id={employee_id}")
    assert list_res.status_code == 200
    rosters_list = list_res.json()
    assert any(r["employee_roster_id"] == roster_id for r in rosters_list)

    # 6. Delete the assigned roster
    del_res = await c.delete(f"/api/v1/rosters/{roster_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_security_roles_and_granular_permissions(client):
    """Test retrieving roles, permissions, and assigning granular permissions to a role."""
    c, session = client

    # 1. List roles
    roles_res = await c.get("/api/v1/security/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) > 0
    test_role = roles[0]
    role_id = test_role["role_id"]

    # 2. List system permissions
    perms_res = await c.get("/api/v1/security/permissions")
    assert perms_res.status_code == 200
    perms = perms_res.json()
    assert len(perms) >= 5

    # Pick 2 permissions to grant
    selected_pids = [p["permission_id"] for p in perms[:2]]

    # 3. Assign permissions to the role
    assign_payload = {
        "permission_ids": selected_pids
    }
    assign_res = await c.post(f"/api/v1/security/roles/{role_id}/permissions", json=assign_payload)
    assert assign_res.status_code == 200
    assign_data = assign_res.json()
    assert assign_data["granted_permissions_count"] == len(selected_pids)

    # 4. Fetch the role's permissions
    role_perms_res = await c.get(f"/api/v1/security/roles/{role_id}/permissions")
    assert role_perms_res.status_code == 200
    role_perms_data = role_perms_res.json()
    assigned_ids = [p["permission_id"] for p in role_perms_data["permissions"]]
    for pid in selected_pids:
        assert pid in assigned_ids


@pytest.mark.asyncio
async def test_document_security_and_integrity_verification(client):
    """Test uploading employee document with SHA-256 calculation and cryptographic tamper check."""
    c, session = client

    # 1. Get an active employee
    emp = await session.scalar(select(Employee).where(Employee.employment_status == "active"))
    if not emp:
        emp = await session.scalar(select(Employee))
    assert emp, "An employee is required"
    employee_id = str(emp.employee_id)

    # 2. Upload a test document
    file_bytes = b"CONFIDENTIAL MEDICAL CERTIFICATE - VERIFICATION HASH 2026"
    expected_sha256 = hashlib.sha256(file_bytes).hexdigest()

    files = [
        ("files", ("medical_cert.pdf", file_bytes, "application/pdf"))
    ]
    data = {
        "document_names": ["Medical Certification"],
        "document_types": ["Certification"]
    }

    upload_res = await c.post(
        f"/api/v1/employee-documents/upload/{employee_id}",
        files=files,
        data=data
    )
    assert upload_res.status_code == 201
    docs = upload_res.json()
    assert len(docs) == 1
    doc = docs[0]
    doc_id = doc["employee_document_id"]
    assert doc["checksum_sha256"] == expected_sha256
    assert doc["file_size_bytes"] == len(file_bytes)
    assert doc["mime_type"] == "application/pdf"

    # 3. Verify document integrity via verification endpoint
    verify_res = await c.get(f"/api/v1/employee-documents/verify/{doc_id}")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    assert verify_data["stored_checksum"] == expected_sha256
    assert verify_data["calculated_checksum"] == expected_sha256
    assert "intact" in verify_data["status"].lower()

