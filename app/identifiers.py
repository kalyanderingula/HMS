from datetime import date

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receptionist_models import Appointment


async def generate_appointment_number(db: AsyncSession, appointment_date: date) -> str:
    """Return APT-YYYYMMDD-NNNN, sequenced across all booking channels."""
    date_part = appointment_date.strftime("%Y%m%d")
    prefix = f"APT-{date_part}-"
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:sequence_key))"),
            {"sequence_key": f"appointment:{date_part}"},
        )
    existing = (await db.execute(
        select(Appointment.appointment_number)
        .where(Appointment.appointment_number.like(f"{prefix}%"))
        .order_by(Appointment.appointment_number.desc())
    )).scalars().all()
    sequences = [int(number[-4:]) for number in existing if number[-4:].isdigit()]
    sequence = max(sequences, default=0) + 1
    if sequence > 9999:
        raise HTTPException(409, "Daily appointment-number sequence is exhausted")
    return f"{prefix}{sequence:04d}"
