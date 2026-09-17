import uuid

import pytest
from fastapi import HTTPException

from app.api.auth import CurrentUser
from app.api.emr import enforce_clinical_read_scope
from app.api.notifications import mark_notification_read
from app.api.telemedicine import enforce_virtual_appointment_access
from app.models.emr_models import VirtualAppointment


def current_user(*, roles, patient_id=None):
    return CurrentUser(
        user_id=uuid.uuid4(),
        patient_id=patient_id,
        username="security-test-user",
        roles=roles,
    )


@pytest.mark.asyncio
async def test_patient_can_read_only_their_own_clinical_record():
    patient_id = uuid.uuid4()
    user = current_user(roles=["patient"], patient_id=patient_id)

    await enforce_clinical_read_scope(user, db=None, patient_id=patient_id)

    with pytest.raises(HTTPException) as exc:
        await enforce_clinical_read_scope(user, db=None, patient_id=uuid.uuid4())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_receptionist_cannot_read_clinical_records():
    user = current_user(roles=["receptionist"])

    with pytest.raises(HTTPException) as exc:
        await enforce_clinical_read_scope(user, db=None, patient_id=uuid.uuid4())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_administrator_can_read_clinical_records():
    user = current_user(roles=["admin"])
    await enforce_clinical_read_scope(user, db=None, patient_id=uuid.uuid4())


class NotificationDbStub:
    def __init__(self, recipient_type=None):
        self.recipient_type = recipient_type
        self.statement = None
        self.params = None
        self.committed = False
        self.executed = []

    async def scalar(self, statement, params):
        self.statement = str(statement)
        self.params = params
        return self.recipient_type

    async def execute(self, statement, params):
        self.executed.append((str(statement), params))

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_user_cannot_mark_an_unowned_notification_read():
    notification_id = uuid.uuid4()
    db = NotificationDbStub(recipient_type=None)
    user = current_user(roles=["doctor"])

    with pytest.raises(HTTPException) as exc:
        await mark_notification_read(notification_id, db=db, cu=user)

    assert exc.value.status_code == 404
    assert db.params["user_id"] == user.user_id
    assert db.params["roles"] == ["doctor"]
    assert "recipient_id=:user_id" in db.statement
    assert db.committed is False


@pytest.mark.asyncio
async def test_owned_notification_can_be_marked_read():
    notification_id = uuid.uuid4()
    db = NotificationDbStub(recipient_type="User")
    user = current_user(roles=["doctor"])

    result = await mark_notification_read(notification_id, db=db, cu=user)

    assert result["notification_id"] == str(notification_id)
    assert db.committed is True
    assert any("UPDATE core.notifications" in statement for statement, _ in db.executed)


@pytest.mark.asyncio
async def test_patient_cannot_access_another_patients_virtual_appointment():
    patient_id = uuid.uuid4()
    appointment = VirtualAppointment(patient_id=uuid.uuid4(), provider_id=uuid.uuid4())
    user = current_user(roles=["patient"], patient_id=patient_id)

    with pytest.raises(HTTPException) as exc:
        await enforce_virtual_appointment_access(appointment, user, db=None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patient_can_access_own_virtual_appointment():
    patient_id = uuid.uuid4()
    appointment = VirtualAppointment(patient_id=patient_id, provider_id=uuid.uuid4())
    user = current_user(roles=["patient"], patient_id=patient_id)

    await enforce_virtual_appointment_access(appointment, user, db=None)
