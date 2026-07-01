from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from app.config import get_db
from app.models.department import Country, State

router = APIRouter(prefix="/locations", tags=["Countries & States"])


class CountryCreate(BaseModel):
    country_code: str
    country_name: str


class CountryResponse(BaseModel):
    country_id: UUID
    country_code: str
    country_name: str
    is_active: Optional[bool]

    class Config:
        from_attributes = True


class StateCreate(BaseModel):
    country_id: UUID
    state_code: str
    state_name: str


class StateResponse(BaseModel):
    state_id: UUID
    country_id: UUID
    state_code: str
    state_name: str
    is_active: Optional[bool]

    class Config:
        from_attributes = True


# --- Countries ---

@router.post("/countries", response_model=CountryResponse, status_code=201)
async def create_country(data: CountryCreate, db: AsyncSession = Depends(get_db)):
    country = Country(**data.model_dump())
    db.add(country)
    await db.commit()
    await db.refresh(country)
    return country


@router.get("/countries", response_model=list[CountryResponse])
async def list_countries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Country).order_by(Country.country_name))
    return result.scalars().all()


# --- States ---

@router.post("/states", response_model=StateResponse, status_code=201)
async def create_state(data: StateCreate, db: AsyncSession = Depends(get_db)):
    country = await db.get(Country, data.country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    state = State(**data.model_dump())
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


@router.get("/states", response_model=list[StateResponse])
async def list_states(country_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    query = select(State).order_by(State.state_name)
    if country_id:
        query = query.where(State.country_id == country_id)
    result = await db.execute(query)
    return result.scalars().all()
