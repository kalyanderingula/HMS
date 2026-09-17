from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.patients import generate_patient_identifiers


def identifier_db(existing_codes=None):
    db = MagicMock()
    db.get_bind.return_value = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    result = MagicMock()
    result.scalars.return_value.all.return_value = existing_codes or []
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_patient_identifier_uses_registration_date_name_and_birth_year():
    db = identifier_db()

    mrn, patient_code = await generate_patient_identifiers(
        db,
        "Kalyan",
        date(1999, 9, 13),
        registration_date=date(2026, 9, 17),
    )

    assert patient_code == "PAT-2026-0917KA1999001"
    assert mrn == "MRN-2026-0917KA1999001"


@pytest.mark.asyncio
async def test_patient_identifier_increments_matching_sequence():
    db = identifier_db(["PAT-2026-0917KA1999002", "PAT-2026-0917KA1999001"])

    mrn, patient_code = await generate_patient_identifiers(
        db,
        "Kalyan",
        date(1999, 9, 13),
        registration_date=date(2026, 9, 17),
    )

    assert patient_code.endswith("003")
    assert mrn.endswith("003")
