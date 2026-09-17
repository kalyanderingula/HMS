from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.identifiers import generate_appointment_number


def identifier_db(existing_numbers=None):
    db = MagicMock()
    db.get_bind.return_value = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    result = MagicMock()
    result.scalars.return_value.all.return_value = existing_numbers or []
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_first_appointment_number_for_date():
    number = await generate_appointment_number(identifier_db(), date(2026, 9, 18))
    assert number == "APT-20260918-0001"


@pytest.mark.asyncio
async def test_appointment_number_increments_daily_sequence():
    db = identifier_db(["APT-20260918-0007", "APT-20260918-0002"])
    number = await generate_appointment_number(db, date(2026, 9, 18))
    assert number == "APT-20260918-0008"
